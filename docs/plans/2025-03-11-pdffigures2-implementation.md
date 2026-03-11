# PDFFigures2 Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate pdffigures2 (Scala-based PDF figure extraction tool) as a replacement for the existing PyMuPDF image extractor in the paper_daily project.

**Architecture:** Create a new `PDFFigures2Extractor` class that calls the pdffigures2 JAR via subprocess, parses JSON output, and returns `ImageMetadata` objects. Use a factory pattern to allow switching between extractors via config.

**Tech Stack:** Python 3.13, asyncio, subprocess, Pydantic, pdffigures2 JAR (Scala/Java)

---

## Prerequisites

**Before starting:**

1. Compile pdffigures2 JAR:
```bash
cd /home/yuyuan/paper_daily/pdffigures2
sbt assembly
# JAR will be at: target/scala-2.13/pdffigures2-assembly-*.jar
```

2. Verify Java is installed:
```bash
java -version
```

---

## Task 1: Update models.py to add fig_type field

**Files:**
- Modify: `src/models.py`

**Step 1: Read the current ImageMetadata model**

Read: `src/models.py`

**Step 2: Add fig_type field to ImageMetadata**

Find the `ImageMetadata` class and add `fig_type` field:

```python
@dataclass
class ImageMetadata:
    """Metadata for an extracted image from a paper."""

    path: Path
    page_number: int
    figure_number: str | None = None
    caption: str | None = None
    fig_type: Literal["Figure", "Table", None] = None  # NEW: Figure/Table type
```

**Step 3: Run tests to ensure no breakage**

Run: `pytest tests/unit/test_models.py -v`
Expected: All tests pass (new field is optional)

**Step 4: Commit**

```bash
git add src/models.py
git commit -m "feat: add fig_type field to ImageMetadata"
```

---

## Task 2: Create PDFFigures2Extractor class

**Files:**
- Create: `src/pdffigures_extractor.py`

**Step 1: Write the failing test**

Create: `tests/unit/test_pdffigures_extractor.py`

```python
import pytest
from pathlib import Path
from pdffigures_extractor import PDFFigures2Extractor
from models import Paper, PaperStatus, ImageMetadata

@pytest.fixture
def mock_jar_path(tmp_path):
    """Create a mock JAR path."""
    jar_path = tmp_path / "pdffigures2.jar"
    jar_path.touch()
    return jar_path

@pytest.fixture
def extractor(mock_jar_path, tmp_path):
    """Create extractor instance."""
    return PDFFigures2Extractor(
        jar_path=mock_jar_path,
        output_dir=tmp_path / "output",
        dpi=150
    )

def test_extractor_init(extractor, mock_jar_path):
    """Test extractor initialization."""
    assert extractor.jar_path == mock_jar_path
    assert extractor.output_dir.name == "output"
    assert extractor.dpi == 150

def test_extractor_init_with_defaults(tmp_path):
    """Test extractor with default values."""
    jar_path = tmp_path / "pdffigures2.jar"
    jar_path.touch()
    extractor = PDFFigures2Extractor(jar_path=jar_path)
    assert extractor.dpi == 150
    assert extractor.extract_figures is True
    assert extractor.extract_tables is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pdffigures_extractor.py -v`
Expected: FAIL with "module 'pdffigures_extractor' not found"

**Step 3: Write minimal PDFFigures2Extractor class**

Create: `src/pdffigures_extractor.py`

```python
"""PDFFigures2 integration for extracting figures from PDF papers."""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from models import Paper, PaperStatus, ImageMetadata

logger = logging.getLogger(__name__)


class PDFFigures2Extractor:
    """Extracts figures and tables from PDFs using pdffigures2 JAR."""

    def __init__(
        self,
        jar_path: Path,
        output_dir: Path,
        dpi: int = 150,
        extract_figures: bool = True,
        extract_tables: bool = True,
        max_figures: int = 20,
        java_options: list[str] | None = None,
    ) -> None:
        """Initialize the pdffigures2 extractor.

        Args:
            jar_path: Path to the pdffigures2-assembly JAR file.
            output_dir: Directory to save extracted images.
            dpi: DPI for rendering images.
            extract_figures: Whether to extract Figure types.
            extract_tables: Whether to extract Table types.
            max_figures: Maximum number of figures to extract.
            java_options: Additional JVM options (e.g., "-Xmx2g").
        """
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.dpi = dpi
        self.extract_figures = extract_figures
        self.extract_tables = extract_tables
        self.max_figures = max_figures
        self.java_options = java_options or [
            "-Xmx2g",
            "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider",
        ]

    async def extract(self, paper: Paper) -> Paper:
        """Extract figures from a paper's PDF.

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            return await asyncio.to_thread(self._extract_sync, paper)
        except Exception:
            logger.exception("Failed to extract figures from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _extract_sync(self, paper: Paper) -> Paper:
        """Synchronous figure extraction.

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        try:
            # Create output directory for this paper
            paper_output_dir = self.output_dir / paper.arxiv_id
            paper_output_dir.mkdir(parents=True, exist_ok=True)

            # Run pdffigures2 in a temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Build command
                cmd = self._build_command(paper.pdf_path, temp_path)

                # Run pdffigures2
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                )

                if result.returncode != 0:
                    logger.warning(
                        "pdffigures2 failed for paper %s: %s",
                        paper.arxiv_id,
                        result.stderr,
                    )
                    paper.status = PaperStatus.images_extracted
                    return paper

                # Parse JSON output
                json_file = self._find_json_output(temp_path)
                if not json_file:
                    logger.warning("No JSON output found for paper %s", paper.arxiv_id)
                    paper.status = PaperStatus.images_extracted
                    return paper

                with open(json_file) as f:
                    figures_data = json.load(f)

                # Process each figure
                for fig_data in figures_data[: self.max_figures]:
                    metadata = self._process_figure(fig_data, paper_output_dir, paper.arxiv_id)
                    if metadata:
                        paper.images.append(metadata)

            paper.status = PaperStatus.images_extracted
            return paper

        except subprocess.TimeoutExpired:
            logger.error("pdffigures2 timeout for paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper
        except Exception:
            logger.exception("Unexpected error extracting figures from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _build_command(self, pdf_path: Path, temp_dir: Path) -> list[str]:
        """Build the pdffigures2 command.

        Args:
            pdf_path: Path to the PDF file.
            temp_dir: Temporary directory for outputs.

        Returns:
            Command as list of strings.
        """
        cmd = ["java"] + self.java_options + [
            "-jar",
            str(self.jar_path),
            str(pdf_path),
            "-m", str(temp_dir / "figures"),  # Image output prefix
            "-d", str(temp_dir / "data"),      # JSON data output prefix
        ]
        return cmd

    def _find_json_output(self, temp_dir: Path) -> Path | None:
        """Find the JSON output file from pdffigures2.

        Args:
            temp_dir: Temporary directory containing outputs.

        Returns:
            Path to JSON file, or None if not found.
        """
        # pdffigures2 creates JSON like: data_output{arxiv_id}.json
        for json_file in temp_dir.glob("*.json"):
            return json_file
        return None

    def _process_figure(
        self, fig_data: dict, output_dir: Path, arxiv_id: str
    ) -> ImageMetadata | None:
        """Process a single figure from pdffigures2 data.

        Args:
            fig_data: Dictionary with figure data from pdffigures2.
            output_dir: Directory to save the renamed image.
            arxiv_id: arXiv ID for the paper.

        Returns:
            ImageMetadata object, or None if processing failed.
        """
        try:
            fig_type = fig_data.get("figType", "Figure")

            # Skip if not requested
            if fig_type == "Figure" and not self.extract_figures:
                return None
            if fig_type == "Table" and not self.extract_tables:
                return None

            # Get original image path
            original_name = fig_data.get("renderURL", "")
            if not original_name:
                return None

            # Find the actual image file in temp dir
            # We need to pass temp_dir to this method - will fix in next step
            # For now, return None to make tests pass
            return None

        except Exception as e:
            logger.debug("Error processing figure: %s", e)
            return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_pdffigures_extractor.py -v`
Expected: PASS for initialization tests

**Step 5: Commit**

```bash
git add src/pdffigures_extractor.py tests/unit/test_pdffigures_extractor.py
git commit -m "feat: add PDFFigures2Extractor class with basic structure"
```

---

## Task 3: Implement figure processing and image renaming

**Files:**
- Modify: `src/pdffigures_extractor.py`
- Modify: `tests/unit/test_pdffigures_extractor.py`

**Step 1: Add test for figure processing**

Add to `tests/unit/test_pdffigures_extractor.py`:

```python
def test_process_figure_renames_image(extractor, tmp_path):
    """Test that figure processing renames images correctly."""
    # Create mock image file
    original_img = tmp_path / "figures_output-test-Figure1-1.png"
    original_img.parent.mkdir(parents=True, exist_ok=True)
    original_img.touch()

    fig_data = {
        "figType": "Figure",
        "name": "1",
        "caption": "Test Figure 1: A test figure.",
        "page": 0,
        "renderURL": str(original_img),
    }

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = extractor._process_figure(fig_data, output_dir, "test")

    assert result is not None
    assert result.fig_type == "Figure"
    assert result.caption == "Test Figure 1: A test figure."
    assert result.page_number == 1
    assert result.figure_number == "1"

def test_process_figure_filters_by_type(extractor, tmp_path):
    """Test that figures are filtered by type."""
    extractor.extract_figures = False  # Disable figure extraction

    original_img = tmp_path / "figures_output-test-Figure1-1.png"
    original_img.parent.mkdir(parents=True, exist_ok=True)
    original_img.touch()

    fig_data = {
        "figType": "Figure",
        "name": "1",
        "caption": "Test Figure 1.",
        "page": 0,
        "renderURL": str(original_img),
    }

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = extractor._process_figure(fig_data, output_dir, "test")

    # Should return None because figures are disabled
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pdffigures_extractor.py::test_process_figure_renames_image -v`
Expected: FAIL - current implementation returns None

**Step 3: Implement full figure processing**

Update `_process_figure` and `_extract_sync` in `src/pdffigures_extractor.py`:

```python
    def _extract_sync(self, paper: Paper) -> Paper:
        """Synchronous figure extraction.

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        try:
            # Create output directory for this paper
            paper_output_dir = self.output_dir / paper.arxiv_id
            paper_output_dir.mkdir(parents=True, exist_ok=True)

            # Run pdffigures2 in a temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Build command
                cmd = self._build_command(paper.pdf_path, temp_path)

                # Run pdffigures2
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                )

                if result.returncode != 0:
                    logger.warning(
                        "pdffigures2 failed for paper %s: %s",
                        paper.arxiv_id,
                        result.stderr,
                    )
                    paper.status = PaperStatus.images_extracted
                    return paper

                # Parse JSON output
                json_file = self._find_json_output(temp_path)
                if not json_file:
                    logger.warning("No JSON output found for paper %s", paper.arxiv_id)
                    paper.status = PaperStatus.images_extracted
                    return paper

                with open(json_file) as f:
                    figures_data = json.load(f)

                # Process each figure - pass temp_path
                for fig_data in figures_data[: self.max_figures]:
                    metadata = self._process_figure(fig_data, paper_output_dir, paper.arxiv_id, temp_path)
                    if metadata:
                        paper.images.append(metadata)

            paper.status = PaperStatus.images_extracted
            return paper

        except subprocess.TimeoutExpired:
            logger.error("pdffigures2 timeout for paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper
        except Exception:
            logger.exception("Unexpected error extracting figures from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _process_figure(
        self, fig_data: dict, output_dir: Path, arxiv_id: str, temp_dir: Path
    ) -> ImageMetadata | None:
        """Process a single figure from pdffigures2 data.

        Args:
            fig_data: Dictionary with figure data from pdffigures2.
            output_dir: Directory to save the renamed image.
            arxiv_id: arXiv ID for the paper.
            temp_dir: Temp directory containing original image files.

        Returns:
            ImageMetadata object, or None if processing failed.
        """
        try:
            fig_type = fig_data.get("figType", "Figure")

            # Skip if not requested
            if fig_type == "Figure" and not self.extract_figures:
                return None
            if fig_type == "Table" and not self.extract_tables:
                return None

            # Get original image path
            original_name = fig_data.get("renderURL", "")
            if not original_name:
                return None

            # Find the actual image file in temp dir
            original_path = temp_dir / Path(original_name).name
            if not original_path.exists():
                logger.debug("Image file not found: %s", original_path)
                return None

            # Generate new filename: Figure1.png, Table1.png, etc.
            fig_name = fig_data.get("name", "")
            new_filename = f"{fig_type}{fig_name}.png"
            new_path = output_dir / new_filename

            # Copy image to output directory with new name
            import shutil
            shutil.copy2(original_path, new_path)

            # Extract caption (remove the figure number prefix)
            caption = fig_data.get("caption", "")
            if caption and ":" in caption:
                # Keep only the part after "Figure 1:" or similar
                caption = caption.split(":", 1)[1].strip()

            # Get page number (convert 0-based to 1-based)
            page = fig_data.get("page", 0) + 1

            return ImageMetadata(
                path=new_path,
                page_number=page,
                figure_number=fig_name,
                caption=caption or None,
                fig_type=fig_type,
            )

        except Exception as e:
            logger.debug("Error processing figure: %s", e)
            return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_pdffigures_extractor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pdffigures_extractor.py tests/unit/test_pdffigures_extractor.py
git commit -m "feat: implement figure processing and image renaming"
```

---

## Task 4: Add error handling for JAR not found

**Files:**
- Modify: `src/pdffigures_extractor.py`
- Modify: `tests/unit/test_pdffigures_extractor.py`

**Step 1: Write test for JAR not found**

Add to `tests/unit/test_pdffigures_extractor.py`:

```python
def test_extract_with_missing_jar(tmp_path):
    """Test extraction fails gracefully when JAR doesn't exist."""
    missing_jar = tmp_path / "nonexistent.jar"
    extractor = PDFFigures2Extractor(
        jar_path=missing_jar,
        output_dir=tmp_path / "output"
    )

    paper = Paper(
        arxiv_id="test",
        title="Test",
        pdf_path=tmp_path / "test.pdf",  # Doesn't matter for this test
    )

    result = extractor._extract_sync(paper)

    assert result.status == PaperStatus.failed
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pdffigures_extractor.py::test_extract_with_missing_jar -v`
Expected: FAIL - JAR check not implemented

**Step 3: Add JAR validation**

Update `src/pdffigures_extractor.py`:

```python
    def _extract_sync(self, paper: Paper) -> Paper:
        """Synchronous figure extraction.

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        # Check if JAR exists
        if not self.jar_path.exists():
            logger.error("pdffigures2 JAR not found at: %s", self.jar_path)
            paper.status = PaperStatus.failed
            return paper

        # Check if PDF exists
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            # Create output directory for this paper
            paper_output_dir = self.output_dir / paper.arxiv_id
            paper_output_dir.mkdir(parents=True, exist_ok=True)

            # ... rest of method unchanged ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_pdffigures_extractor.py::test_extract_with_missing_jar -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pdffigures_extractor.py tests/unit/test_pdffigures_extractor.py
git commit -m "feat: add JAR validation to PDFFigures2Extractor"
```

---

## Task 5: Update config.py to support pdffigures2 configuration

**Files:**
- Modify: `src/config.py`

**Step 1: Read current config structure**

Read: `src/config.py`

**Step 2: Add pdffigures2 configuration parsing**

Add the VisionConfig dataclass and pdffigures2 settings. After reading the file, locate the vision config section and extend it:

```python
@dataclass
class VisionConfig:
    """Configuration for image extraction and analysis."""

    enabled: bool = False
    extractor: Literal["pymupdf", "pdffigures2"] = "pymupdf"

    # PyMuPDF extractor options
    min_size: tuple[int, int] = (100, 100)
    max_aspect_ratio: float = 5.0
    max_images_per_paper: int = 15

    # PDFFigures2 extractor options
    pdffigures2_jar: str | None = None
    pdffigures2_dpi: int = 150
    pdffigures2_extract_figures: bool = True
    pdffigures2_extract_tables: bool = True
    pdffigures2_max_figures: int = 20
    pdffigures2_java_options: list[str] | None = None

    # Image analysis (optional)
    analysis: dict | None = None
```

**Step 3: Run tests to ensure config still loads**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/config.py
git commit -m "feat: add pdffigures2 configuration options"
```

---

## Task 6: Create ExtractorFactory

**Files:**
- Create: `src/extractor_factory.py`

**Step 1: Write test for factory**

Create: `tests/unit/test_extractor_factory.py`

```python
import pytest
from pathlib import Path
from extractor_factory import ExtractorFactory
from image_extractor import ImageExtractor
from pdffigures_extractor import PDFFigures2Extractor

def test_factory_creates_pymupdf_extractor(tmp_path):
    """Test factory creates PyMuPDF extractor when configured."""
    config = {
        "enabled": True,
        "extractor": "pymupdf",
        "min_size": (200, 200),
        "max_aspect_ratio": 3.0,
        "max_images_per_paper": 10,
    }

    extractor = ExtractorFactory.create(config, tmp_path / "output")

    assert isinstance(extractor, ImageExtractor)
    assert extractor.min_size == (200, 200)

def test_factory_creates_pdffigures2_extractor(tmp_path):
    """Test factory creates pdffigures2 extractor when configured."""
    jar_path = tmp_path / "pdffigures2.jar"
    jar_path.touch()

    config = {
        "enabled": True,
        "extractor": "pdffigures2",
        "pdffigures2_jar": str(jar_path),
        "pdffigures2_dpi": 200,
    }

    extractor = ExtractorFactory.create(config, tmp_path / "output")

    assert isinstance(extractor, PDFFigures2Extractor)
    assert extractor.dpi == 200

def test_factory_defaults_to_pymupdf(tmp_path):
    """Test factory defaults to PyMuPDF when not specified."""
    config = {"enabled": True}

    extractor = ExtractorFactory.create(config, tmp_path / "output")

    assert isinstance(extractor, ImageExtractor)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_extractor_factory.py -v`
Expected: FAIL with "module 'extractor_factory' not found"

**Step 3: Implement ExtractorFactory**

Create: `src/extractor_factory.py`

```python
"""Factory for creating image extractor instances."""

from pathlib import Path
from typing import Literal

from config import VisionConfig
from image_extractor import ImageExtractor
from pdffigures_extractor import PDFFigures2Extractor


class ExtractorFactory:
    """Factory for creating image extractor instances based on configuration."""

    @staticmethod
    def create(
        config: VisionConfig | dict, output_dir: Path
    ) -> ImageExtractor | PDFFigures2Extractor:
        """Create an image extractor based on configuration.

        Args:
            config: Vision configuration (VisionConfig or dict).
            output_dir: Base directory for image output.

        Returns:
            An image extractor instance.

        Raises:
            ValueError: If extractor type is unknown.
        """
        # Handle dict input
        if isinstance(config, dict):
            extractor_type = config.get("extractor", "pymupdf")
        else:
            extractor_type = config.extractor

        if extractor_type == "pymupdf":
            return ExtractorFactory._create_pymupdf_extractor(config, output_dir)
        elif extractor_type == "pdffigures2":
            return ExtractorFactory._create_pdffigures2_extractor(config, output_dir)
        else:
            raise ValueError(f"Unknown extractor type: {extractor_type}")

    @staticmethod
    def _create_pymupdf_extractor(
        config: VisionConfig | dict, output_dir: Path
    ) -> ImageExtractor:
        """Create a PyMuPDF-based extractor.

        Args:
            config: Vision configuration.
            output_dir: Base directory for image output.

        Returns:
            ImageExtractor instance.
        """
        if isinstance(config, dict):
            return ImageExtractor(
                min_size=config.get("min_size", (100, 100)),
                max_aspect_ratio=config.get("max_aspect_ratio", 5.0),
                max_images_per_paper=config.get("max_images_per_paper", 15),
                output_dir=output_dir,
            )
        else:
            return ImageExtractor(
                min_size=config.min_size,
                max_aspect_ratio=config.max_aspect_ratio,
                max_images_per_paper=config.max_images_per_paper,
                output_dir=output_dir,
            )

    @staticmethod
    def _create_pdffigures2_extractor(
        config: VisionConfig | dict, output_dir: Path
    ) -> PDFFigures2Extractor:
        """Create a pdffigures2-based extractor.

        Args:
            config: Vision configuration.
            output_dir: Base directory for image output.

        Returns:
            PDFFigures2Extractor instance.

        Raises:
            ValueError: If JAR path is not configured.
        """
        if isinstance(config, dict):
            jar_path = config.get("pdffigures2_jar")
            if not jar_path:
                raise ValueError("pdffigures2_jar must be configured")
            return PDFFigures2Extractor(
                jar_path=Path(jar_path),
                output_dir=output_dir,
                dpi=config.get("pdffigures2_dpi", 150),
                extract_figures=config.get("pdffigures2_extract_figures", True),
                extract_tables=config.get("pdffigures2_extract_tables", True),
                max_figures=config.get("pdffigures2_max_figures", 20),
                java_options=config.get("pdffigures2_java_options"),
            )
        else:
            jar_path = config.pdffigures2_jar
            if not jar_path:
                raise ValueError("pdffigures2_jar must be configured")
            return PDFFigures2Extractor(
                jar_path=Path(jar_path),
                output_dir=output_dir,
                dpi=config.pdffigures2_dpi,
                extract_figures=config.pdffigures2_extract_figures,
                extract_tables=config.pdffigures2_extract_tables,
                max_figures=config.pdffigures2_max_figures,
                java_options=config.pdffigures2_java_options,
            )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_extractor_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/extractor_factory.py tests/unit/test_extractor_factory.py
git commit -m "feat: add ExtractorFactory for creating extractors"
```

---

## Task 7: Update runner.py to use ExtractorFactory

**Files:**
- Modify: `src/runner.py`

**Step 1: Read current runner.py**

Read: `src/runner.py` to understand how ImageExtractor is currently created.

**Step 2: Update runner to use factory**

Find where `ImageExtractor` is instantiated and replace with factory usage. Look for code like:

```python
# OLD CODE (example):
extractor = ImageExtractor(
    min_size=config.vision.min_size,
    max_aspect_ratio=config.vision.max_aspect_ratio,
    max_images_per_paper=config.vision.max_images_per_paper,
    output_dir=Path("data/images"),
)
```

Replace with:

```python
# NEW CODE:
from extractor_factory import ExtractorFactory

extractor = ExtractorFactory.create(
    config.vision,
    output_dir=Path("data/images"),
)
```

**Step 3: Run tests to ensure runner still works**

Run: `pytest tests/unit/test_runner.py -v` (if exists) or `pytest tests/integration/test_pipeline.py -v`

Expected: PASS

**Step 4: Commit**

```bash
git add src/runner.py
git commit -m "refactor: use ExtractorFactory to create extractor instances"
```

---

## Task 8: Update renderer.py to support Figure/Table display

**Files:**
- Modify: `src/renderer.py`

**Step 1: Read current renderer.py**

Read: `src/renderer.py` to understand how figures are currently rendered.

**Step 2: Add Figure/Table type indicators**

Find the figure rendering section and add type indicators. Look for markdown generation code like:

```python
# Example existing code - adapt to actual structure:
for image in paper.images:
    markdown += f"### {image.figure_number}\n\n"
    markdown += f"![Figure {image.figure_number}]({image.path})\n\n"
    if image.caption:
        markdown += f"*{image.caption}*\n\n"
```

Update to:

```python
for image in paper.images:
    # Add type indicator (Figure/Table)
    fig_type = image.fig_type or "Figure"
    markdown += f"### {fig_type} {image.figure_number}\n\n"
    markdown += f"![{fig_type} {image.figure_number}]({image.path})\n\n"
    if image.caption:
        markdown += f"*{image.caption}*\n\n"
```

**Step 3: Run tests to verify rendering**

Run: `pytest tests/unit/test_renderer.py -v`

Expected: PASS

**Step 4: Commit**

```bash
git add src/renderer.py
git commit -m "feat: add Figure/Table type indicators in rendered output"
```

---

## Task 9: Update example config with pdffigures2 settings

**Files:**
- Modify: `config/config.yaml` (or create example config)

**Step 1: Check existing config structure**

Read: `config/config.yaml`

**Step 2: Add pdffigures2 configuration example**

Add/update the vision section:

```yaml
# Image extraction and analysis
vision:
  enabled: true
  extractor: pdffigures2  # Options: "pymupdf" or "pdffigures2"

  # PyMuPDF extractor options (when extractor: pymupdf)
  extraction:
    min_size: [100, 100]
    max_aspect_ratio: 5.0
    max_images_per_paper: 15

  # PDFFigures2 extractor options (when extractor: pdffigures2)
  pdffigures2_jar: "/path/to/pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar"
  pdffigures2_dpi: 150
  pdffigures2_extract_figures: true
  pdffigures2_extract_tables: true
  pdffigures2_max_figures: 20
  pdffigures2_java_options:
    - "-Xmx2g"
    - "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider"
```

**Step 3: Test config loads correctly**

Run: `python -c "from src.config import load_config; c = load_config('config/config.yaml'); print(c.vision.extractor)"`

Expected: Prints "pdffigures2"

**Step 4: Commit**

```bash
git add config/config.yaml
git commit -m "docs: add pdffigures2 configuration example"
```

---

## Task 10: Update README.md documentation

**Files:**
- Modify: `README.md`

**Step 1: Add pdffigures2 section to README**

Add after the existing vision configuration section:

```markdown
### PDFFigures2 Integration

The project supports two image extraction backends:

1. **PyMuPDF (default)**: Fast Python-based extraction using PyMuPDF
2. **PDFFigures2**: More precise extraction with better caption detection and Figure/Table classification

#### Using PDFFigures2

First, compile the JAR:

```bash
cd pdffigures2
sbt assembly
```

Then configure in `config.yaml`:

```yaml
vision:
  enabled: true
  extractor: pdffigures2
  pdffigures2_jar: "/path/to/pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar"
```

**Benefits of PDFFigures2:**
- Better figure boundary detection
- Accurate caption extraction
- Automatic Figure/Table classification
- Handles multi-column layouts better

**Output naming:**
- PyMuPDF: `figure_{page}_{index}.png`
- PDFFigures2: `Figure1.png`, `Table1.png`, etc.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add pdffigures2 integration documentation"
```

---

## Task 11: Integration test with real PDF

**Files:**
- Modify: `tests/integration/test_image_pipeline.py` (or create new test)

**Step 1: Create integration test**

Create: `tests/integration/test_pdffigures_integration.py`

```python
import pytest
from pathlib import Path
from pdffigures_extractor import PDFFigures2Extractor
from models import Paper, PaperStatus

@pytest.fixture
def real_pdf(tmp_path):
    """Use a real PDF from test data."""
    # Update this path to an actual test PDF
    pdf_path = Path("tests/fixtures/sample.pdf")
    if not pdf_path.exists():
        pytest.skip("Test PDF not found")
    return pdf_path

@pytest.fixture
def jar_path():
    """Path to compiled pdffigures2 JAR."""
    jar = Path("pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar")
    matching = list(jar.parent.glob(jar.name))
    if not matching:
        pytest.skip("pdffigures2 JAR not found. Run: cd pdffigures2 && sbt assembly")
    return matching[0]

def test_extract_from_real_pdf(real_pdf, jar_path, tmp_path):
    """Test extraction from a real PDF file."""
    extractor = PDFFigures2Extractor(
        jar_path=jar_path,
        output_dir=tmp_path / "output",
    )

    paper = Paper(
        arxiv_id="test-sample",
        title="Sample Paper",
        pdf_path=real_pdf,
    )

    result = extractor._extract_sync(paper)

    assert result.status == PaperStatus.images_extracted
    assert len(result.images) > 0

    # Check first image has expected metadata
    first_image = result.images[0]
    assert first_image.path.exists()
    assert first_image.fig_type in ["Figure", "Table"]
    assert first_image.page_number > 0
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_pdffigures_integration.py -v`

Expected: PASS (if JAR is compiled and test PDF exists)

**Step 3: Commit**

```bash
git add tests/integration/test_pdffigures_integration.py
git commit -m "test: add pdffigures2 integration test"
```

---

## Verification

After completing all tasks:

1. **Compile pdffigures2 JAR** (if not already done):
```bash
cd pdffigures2
sbt assembly
```

2. **Update config to use pdffigures2**:
```yaml
vision:
  enabled: true
  extractor: pdffigures2
  pdffigures2_jar: "/path/to/pdffigures2/target/scala-2.13/pdffigures2-assembly-0.0.9-SNAPSHOT.jar"
```

3. **Run full pipeline test**:
```bash
pytest tests/ -v
```

4. **Test with real paper**:
```bash
paper-daily --config config/config.yaml --max-papers 1
```

5. **Verify output**:
- Check `data/images/{arxiv_id}/` for extracted images
- Verify filenames are like `Figure1.png`, `Table1.png`
- Check summary markdown includes figure captions with type indicators

---

## Summary

This implementation:
- ✅ Creates `PDFFigures2Extractor` class with async support
- ✅ Uses factory pattern for extractor selection
- ✅ Supports Figure/Table classification
- ✅ Simplifies image naming (`Figure1.png`, `Table1.png`)
- ✅ Handles errors gracefully (missing JAR, timeouts)
- ✅ Maintains backward compatibility with PyMuPDF extractor
- ✅ Includes comprehensive unit and integration tests
