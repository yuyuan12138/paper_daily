# Image Extraction and Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add image extraction and multimodal LLM analysis to the AutoPaper pipeline. Extract figures from PDFs, analyze them with vision-capable LLMs, and embed figure descriptions in summaries.

**Architecture:** Two-pass pipeline - first extract images using PyMuPDF with smart filtering, then analyze with configurable multimodal LLM (OpenAI GPT-4o or Anthropic Claude). Images stored per-paper in data/images/{arxiv_id}/.

**Tech Stack:** PyMuPDF (fitz), Pillow, OpenAI SDK, Anthropic SDK, Pydantic

---

## Phase 1: Data Models and Configuration

### Task 1: Add Image Metadata Models

**Files:**
- Modify: `src/models.py:1-38`

**Step 1: Write the failing test**

```bash
# Create test file
cat > tests/unit/test_image_models.py << 'EOF'
"""Tests for image metadata models."""
import pytest
from src.models import ImageMetadata, ImageAnalysis, PaperStatus

def test_image_metadata_creation():
    """Test ImageMetadata can be created."""
    from pathlib import Path
    img = ImageMetadata(
        path=Path("test.png"),
        page_number=3,
        figure_number="Figure 1",
        caption="Architecture diagram",
        image_type="figure"
    )
    assert img.page_number == 3
    assert img.figure_number == "Figure 1"

def test_image_analysis_creation():
    """Test ImageAnalysis can be created."""
    analysis = ImageAnalysis(
        description="A neural network architecture",
        key_findings=["Model A outperforms B"],
        relevance="high"
    )
    assert analysis.relevance == "high"

def test_paper_status_includes_image_stages():
    """Test PaperStatus enum has image stages."""
    assert hasattr(PaperStatus, "images_extracted")
    assert hasattr(PaperStatus, "images_analyzed")
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_models.py -v
```

Expected: FAIL with "cannot import ImageMetadata"

**Step 3: Write minimal implementation**

Edit `src/models.py` to add the new models:

```python
# Add after PaperStatus enum
class PaperStatus(Enum):
    discovered = "discovered"
    downloaded = "downloaded"
    parsed = "parsed"
    images_extracted = "images_extracted"    # NEW
    images_analyzed = "images_analyzed"     # NEW
    summarized = "summarized"
    failed = "failed"

# Add new dataclasses
@dataclass
class ImageAnalysis:
    """Analysis result from multimodal LLM."""
    description: str
    key_findings: list[str]
    relevance: str  # "high" | "medium" | "low"

@dataclass
class ImageMetadata:
    """Metadata for an extracted image."""
    path: Path
    page_number: int
    figure_number: str | None = None
    caption: str | None = None
    analysis: ImageAnalysis | None = None
    image_type: str = "unknown"

# Update Paper dataclass - add images field
@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    submitted_date: datetime
    categories: list[str]
    pdf_url: str
    pdf_path: Path | None = None
    parsed_text: str | None = None
    summary: dict[str, Any] | None = None
    status: PaperStatus = PaperStatus.discovered
    images: list[ImageMetadata] = None  # NEW

    def __post_init__(self):
        if self.images is None:
            self.images = []

# Update exports
__all__ = ["Paper", "PaperStatus", "ImageMetadata", "ImageAnalysis"]
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_models.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/models.py tests/unit/test_image_models.py && git commit -m "feat: add image metadata models and paper status stages"
```

---

### Task 2: Add Vision Configuration

**Files:**
- Modify: `src/config.py:1-74`

**Step 1: Write the failing test**

```bash
cat > tests/unit/test_vision_config.py << 'EOF'
"""Tests for vision configuration."""
import pytest
from src.config import Config, VisionConfig

def test_vision_config_validation():
    """Test VisionConfig can be parsed."""
    config_data = {
        "query": {"keywords": ["test"]},
        "vision": {
            "enabled": True,
            "analysis": {
                "provider": "openai",
                "model_name": "gpt-4o",
                "api_key_env": "OPENAI_API_KEY"
            }
        }
    }
    config = Config(**config_data)
    assert config.vision.enabled == True
    assert config.vision.analysis.provider == "openai"

def test_vision_disabled_by_default():
    """Test vision is disabled when not specified."""
    config_data = {"query": {"keywords": ["test"]}}
    config = Config(**config_data)
    assert config.vision.enabled == False
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_vision_config.py -v
```

Expected: FAIL with "vision"

**Step 3: Write minimal implementation**

Edit `src/config.py` - add new config classes:

```python
# Add after OutputConfig class
class VisionExtractionConfig(BaseModel):
    """Configuration for image extraction."""
    min_size: tuple[int, int] = (200, 200)
    max_aspect_ratio: float = 3.0
    max_images_per_paper: int = Field(gt=0, le=50, default=20)
    skip_duplicates: bool = True

class VisionAnalysisConfig(BaseModel):
    """Configuration for image analysis."""
    provider: str = Field(regex="^(openai|anthropic)$", default="openai")
    model_name: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    max_tokens: int = Field(gt=0, le=4000, default=1000)
    batch_size: int = Field(gt=0, le=10, default=5)
    include_context: bool = True

class VisionStorageConfig(BaseModel):
    """Configuration for image storage."""
    output_dir: Path = Path("./data/images")
    format: str = "png"

class VisionConfig(BaseModel):
    """Configuration for vision/image processing."""
    enabled: bool = False
    extraction: VisionExtractionConfig = Field(default_factory=VisionExtractionConfig)
    analysis: VisionAnalysisConfig | None = None
    storage: VisionStorageConfig = Field(default_factory=VisionStorageConfig)

# Update Config class to include vision
class Config(BaseModel):
    query: QueryConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)  # NEW
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_vision_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/config.py tests/unit/test_vision_config.py && git commit -m "feat: add vision configuration models"
```

---

## Phase 2: Image Extraction Module

### Task 3: Create ImageExtractor Module

**Files:**
- Create: `src/image_extractor.py`
- Test: `tests/unit/test_image_extractor.py`

**Step 1: Write the failing test**

```bash
cat > tests/unit/test_image_extractor.py << 'EOF'
"""Tests for image extraction."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.image_extractor import ImageExtractor
from src.models import Paper, PaperStatus

@pytest.fixture
def extractor():
    return ImageExtractor(
        min_size=(200, 200),
        max_images_per_paper=5,
        output_dir=Path("/tmp/test_images")
    )

@pytest.mark.asyncio
async def test_extractor_initialization():
    """Test ImageExtractor can be initialized."""
    extractor = ImageExtractor()
    assert extractor.min_size == (200, 200)
    assert extractor.max_images_per_paper == 20  # default

def test_extractor_filters_small_images():
    """Test small images are filtered."""
    extractor = ImageExtractor(min_size=(100, 100))
    # An image smaller than min_size should be filtered
    assert extractor._should_include_image(50, 50, 0.5) == False
    # An image larger should pass
    assert extractor._should_include_image(200, 200, 1.0) == True
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_extractor.py -v
```

Expected: FAIL with "cannot import ImageExtractor"

**Step 3: Write minimal implementation**

Create `src/image_extractor.py`:

```python
"""Image extraction from PDFs using PyMuPDF."""

import logging
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from src.models import Paper, PaperStatus, ImageMetadata

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Extracts images from PDF with smart filtering."""

    def __init__(
        self,
        min_size: tuple[int, int] = (200, 200),
        max_aspect_ratio: float = 3.0,
        max_images_per_paper: int = 20,
        skip_duplicates: bool = True,
        output_dir: Path = Path("data/images"),
    ) -> None:
        self.min_size = min_size
        self.max_aspect_ratio = max_aspect_ratio
        self.max_images_per_paper = max_images_per_paper
        self.skip_duplicates = skip_duplicates
        self.output_dir = output_dir
        self._seen_hashes: set[str] = set()

    def _should_include_image(self, width: int, height: int, y_position_ratio: float) -> bool:
        """Apply smart filters to determine if image should be included."""
        # Size filter
        if width < self.min_size[0] or height < self.min_size[1]:
            return False

        # Aspect ratio filter
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > self.max_aspect_ratio:
            return False

        # Position filter - skip header/footer (top/bottom 10%)
        if y_position_ratio < 0.1 or y_position_ratio > 0.9:
            return False

        return True

    async def extract(self, paper: Paper) -> Paper:
        """Extract images from PDF and update paper with ImageMetadata list."""
        if not paper.pdf_path or not paper.pdf_path.exists():
            logger.warning(f"PDF not found for {paper.arxiv_id}")
            paper.status = PaperStatus.failed
            return paper

        try:
            # Create output directory for this paper
            paper_image_dir = self.output_dir / paper.arxiv_id
            paper_image_dir.mkdir(parents=True, exist_ok=True)

            doc = fitz.open(str(paper.pdf_path))
            images: list[ImageMetadata] = []
            self._seen_hashes.clear()

            for page_num, page in enumerate(doc):
                image_list = page.get_images(full=True)
                page_height = page.rect.height

                for img_idx, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        width = base_image["width"]
                        height = base_image["height"]

                        # Get approximate y position
                        img_rects = [r for r in page.get_image_rects(xref)]
                        if img_rects:
                            y_pos = img_rects[0].y0 / page_height
                        else:
                            y_pos = 0.5

                        # Apply filters
                        if not self._should_include_image(width, height, y_pos):
                            continue

                        # Skip duplicates if enabled
                        if self.skip_duplicates:
                            img_hash = f"{width}x{height}"
                            if img_hash in self._seen_hashes:
                                continue
                            self._seen_hashes.add(img_hash)

                        # Save image
                        img_name = f"figure_{page_num}_{img_idx}.png"
                        img_path = paper_image_dir / img_name

                        with open(img_path, "wb") as f:
                            f.write(base_image["image"])

                        images.append(ImageMetadata(
                            path=img_path,
                            page_number=page_num + 1,
                            image_type="figure"
                        ))

                        if len(images) >= self.max_images_per_paper:
                            break

                    except Exception as e:
                        logger.debug(f"Failed to extract image {img_idx} from page {page_num}: {e}")
                        continue

                if len(images) >= self.max_images_per_paper:
                    break

            doc.close()
            paper.images = images
            paper.status = PaperStatus.images_extracted
            logger.info(f"Extracted {len(images)} images from {paper.arxiv_id}")
            return paper

        except Exception as e:
            logger.error(f"Error extracting images from {paper.arxiv_id}: {e}")
            paper.status = PaperStatus.failed
            return paper
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_extractor.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/image_extractor.py tests/unit/test_image_extractor.py && git commit -m "feat: add image extraction module with smart filtering"
```

---

## Phase 3: Image Analysis Module

### Task 4: Create ImageAnalyzer Module

**Files:**
- Create: `src/image_analyzer.py`
- Test: `tests/unit/test_image_analyzer.py`

**Step 1: Write the failing test**

```bash
cat > tests/unit/test_image_analyzer.py << 'EOF'
"""Tests for image analysis."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.image_analyzer import ImageAnalyzer
from src.models import Paper, PaperStatus, ImageMetadata, ImageAnalysis

@pytest.fixture
def analyzer():
    return ImageAnalyzer(
        provider="openai",
        model_name="gpt-4o",
        api_key_env="OPENAI_API_KEY"
    )

def test_analyzer_initialization():
    """Test ImageAnalyzer can be initialized."""
    analyzer = ImageAnalyzer(provider="openai", model_name="gpt-4o")
    assert analyzer.provider == "openai"
    assert analyzer.model_name == "gpt-4o"

@pytest.mark.asyncio
async def test_analyze_empty_images():
    """Test analyzer handles paper with no images."""
    paper = Paper(
        arxiv_id="test.001",
        title="Test",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=None,
        categories=[],
        pdf_url="",
        images=[]
    )
    analyzer = ImageAnalyzer(provider="openai", model_name="gpt-4o")
    result = await analyzer.analyze(paper)
    assert result.status == PaperStatus.images_analyzed
    assert len(result.images) == 0
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_analyzer.py -v
```

Expected: FAIL with "cannot import ImageAnalyzer"

**Step 3: Write minimal implementation**

Create `src/image_analyzer.py`:

```python
"""Image analysis using multimodal LLMs."""

import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from src.config import VisionAnalysisConfig
from src.models import Paper, PaperStatus, ImageMetadata, ImageAnalysis

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Analyzes paper images using multimodal LLM."""

    def __init__(
        self,
        provider: str = "openai",
        model_name: str = "gpt-4o",
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        max_tokens: int = 1000,
        batch_size: int = 5,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.batch_size = batch_size

    async def analyze(self, paper: Paper) -> Paper:
        """Analyze all extracted images."""
        if not paper.images:
            logger.info(f"No images to analyze for {paper.arxiv_id}")
            paper.status = PaperStatus.images_analyzed
            return paper

        try:
            # Process images in batches
            for i in range(0, len(paper.images), self.batch_size):
                batch = paper.images[i:i + self.batch_size]
                await self._analyze_batch(paper, batch)

            paper.status = PaperStatus.images_analyzed
            logger.info(f"Analyzed {len(paper.images)} images for {paper.arxiv_id}")
            return paper

        except Exception as e:
            logger.error(f"Error analyzing images for {paper.arxiv_id}: {e}")
            # Don't fail the whole paper - keep images but mark as extracted only
            paper.status = PaperStatus.images_extracted
            return paper

    async def _analyze_batch(self, paper: Paper, images: list[ImageMetadata]) -> None:
        """Analyze a batch of images."""
        for img in images:
            try:
                analysis = await self._analyze_single_image(paper, img)
                img.analysis = analysis
            except Exception as e:
                logger.warning(f"Failed to analyze image {img.path}: {e}")

    async def _analyze_single_image(self, paper: Paper, img: ImageMetadata) -> ImageAnalysis:
        """Analyze a single image using the LLM."""
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {self.api_key_env}")

        if self.provider == "openai":
            return await self._analyze_with_openai(paper, img, api_key)
        elif self.provider == "anthropic":
            return await self._analyze_with_anthropic(paper, img, api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _analyze_with_openai(self, paper: Paper, img: ImageMetadata, api_key: str) -> ImageAnalysis:
        """Analyze image using OpenAI vision."""
        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**client_kwargs)

        try:
            # Read image as base64
            import base64
            with open(img.path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            prompt = self._create_analysis_prompt(paper, img)

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are analyzing research paper figures."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            return self._parse_analysis_response(content)

        finally:
            await client.close()

    async def _analyze_with_anthropic(self, paper: Paper, img: ImageMetadata, api_key: str) -> ImageAnalysis:
        """Analyze image using Anthropic Claude vision."""
        import base64
        from anthropic import AsyncAnthropic

        with open(img.path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")

        prompt = self._create_analysis_prompt(paper, img)

        client = AsyncAnthropic(api_key=api_key)
        try:
            response = await client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_data
                                }
                            }
                        ]
                    }
                ]
            )
            return self._parse_analysis_response(response.content[0].text)
        finally:
            await client.close()

    def _create_analysis_prompt(self, paper: Paper, img: ImageMetadata) -> str:
        """Create prompt for image analysis."""
        caption_text = f"\nFigure Caption: {img.caption}" if img.caption else ""

        return f"""You are analyzing a research paper figure.

Paper Title: {paper.title}
{caption_text}

Describe this image and identify:
1. What type of visual is this? (figure/table/chart/graph/diagram)
2. What are the key components or data shown?
3. What insight or conclusion does this image support?

Respond in JSON format:
{{
  "image_type": "figure|table|chart|graph|diagram|unknown",
  "description": "Clear visual description",
  "key_findings": ["finding1", "finding2"],
  "relevance": "high|medium|low"
}}"""

    def _parse_analysis_response(self, content: str) -> ImageAnalysis:
        """Parse LLM response into ImageAnalysis."""
        # Extract JSON from response
        json_text = content.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("```")[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
            json_text = json_text.strip()

        data = json.loads(json_text)
        return ImageAnalysis(
            description=data.get("description", ""),
            key_findings=data.get("key_findings", []),
            relevance=data.get("relevance", "medium")
        )
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_image_analyzer.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/image_analyzer.py tests/unit/test_image_analyzer.py && git commit -m "feat: add image analysis module with multimodal LLM support"
```

---

## Phase 4: Pipeline Integration

### Task 5: Update Runner to Include Image Processing

**Files:**
- Modify: `src/runner.py:1-142`
- Test: `tests/integration/test_image_pipeline.py`

**Step 1: Write the failing test**

```bash
cat > tests/integration/test_image_pipeline.py << 'EOF'
"""Integration tests for image pipeline."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.runner import PipelineRunner
from src.config import Config
from src.models import Paper, PaperStatus

@pytest.mark.asyncio
async def test_runner_initializes_with_vision():
    """Test PipelineRunner initializes with image modules."""
    config_data = {
        "query": {"keywords": ["test"]},
        "vision": {"enabled": True, "analysis": {"provider": "openai", "model_name": "gpt-4o", "api_key_env": "TEST_KEY"}}
    }
    config = Config(**config_data)
    runner = PipelineRunner(config)
    assert hasattr(runner, 'image_extractor')
    assert hasattr(runner, 'image_analyzer')

@pytest.mark.asyncio
async def test_runner_skips_vision_when_disabled():
    """Test PipelineRunner skips image processing when disabled."""
    config_data = {"query": {"keywords": ["test"]}, "vision": {"enabled": False}}
    config = Config(**config_data)
    runner = PipelineRunner(config)
    # Should not have image modules when disabled
    assert runner.config.vision.enabled == False
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/integration/test_image_pipeline.py -v
```

Expected: FAIL with "has no attribute 'image_extractor'"

**Step 3: Write minimal implementation**

Edit `src/runner.py` - add imports and modify PipelineRunner:

```python
# Add imports
from src.image_extractor import ImageExtractor
from src.image_analyzer import ImageAnalyzer

# Modify PipelineRunner.__init__
class PipelineRunner:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.state = StateManager(Path("state/paper_state.json"))
        self.state.load()

        # Initialize modules
        self.fetcher = ArXivFetcher(config.query)
        self.downloader = PDFDownloader(
            base_dir=config.output.base_dir,
            retry_times=config.runtime.retry_times,
            timeout_sec=config.runtime.timeout_sec,
        )
        self.parser = PDFParser()
        self.summarizer = PaperSummarizer(
            model_config=config.model,
            language=config.pipeline.language,
            summary_level=config.pipeline.summary_level,
        )
        self.renderer = MarkdownRenderer(
            output_dir=config.output.base_dir / "summaries"
        )

        # NEW: Initialize image modules if enabled
        if config.vision.enabled:
            self.image_extractor = ImageExtractor(
                min_size=config.vision.extraction.min_size,
                max_aspect_ratio=config.vision.extraction.max_aspect_ratio,
                max_images_per_paper=config.vision.extraction.max_images_per_paper,
                skip_duplicates=config.vision.extraction.skip_duplicates,
                output_dir=config.vision.storage.output_dir,
            )
            self.image_analyzer = ImageAnalyzer(
                provider=config.vision.analysis.provider,
                model_name=config.vision.analysis.model_name,
                api_key_env=config.vision.analysis.api_key_env,
                base_url=config.vision.analysis.base_url,
                max_tokens=config.vision.analysis.max_tokens,
                batch_size=config.vision.analysis.batch_size,
            )
```

Now modify the `run` method to add image processing between parse and summarize:

```python
# In the process loop, after parsing and before summarizing:
# Parse
if self.config.pipeline.parse_pdf:
    paper = await self.parser.parse(paper)
    self.state.update_paper_status(paper.arxiv_id, paper.status)
    if paper.status == PaperStatus.failed:
        failed.append(paper.arxiv_id)
        continue

# NEW: Extract images
if self.config.vision.enabled and self.config.pipeline.parse_pdf:
    try:
        paper = await self.image_extractor.extract(paper)
        self.state.update_paper_status(paper.arxiv_id, paper.status)

        if paper.images and self.config.vision.analysis:
            paper = await self.image_analyzer.analyze(paper)
            self.state.update_paper_status(paper.arxiv_id, paper.status)
    except Exception as e:
        logger.warning(f"Image processing failed for {paper.arxiv_id}: {e}")
        # Continue with text-only summary

# Summarize
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/integration/test_image_pipeline.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/runner.py tests/integration/test_image_pipeline.py && git commit -m "feat: integrate image extraction and analysis into pipeline"
```

---

## Phase 5: Summary Integration

### Task 6: Update Summarizer to Include Image Context

**Files:**
- Modify: `src/summarizer.py`
- Create: `prompts/image_analysis.md`

**Step 1: Write the failing test**

```bash
cat > tests/unit/test_summarizer_with_images.py << 'EOF'
"""Tests for summarizer with image context."""
import pytest
from pathlib import Path
from unittest.mock import patch
from src.summarizer import PaperSummarizer

def test_summarizer_creates_prompt_with_images():
    """Test summarizer includes images in prompt."""
    summarizer = PaperSummarizer(
        model_config=MagicMock(provider="openai", model_name="test", api_key_env="TEST", base_url=None, temperature=0.2, max_tokens=1000),
        language="en",
        summary_level="standard"
    )

    # Check that the prompt creation can handle images
    prompt = summarizer._create_prompt_with_images_context([
        {"description": "Test figure", "key_findings": ["Finding 1"]}
    ])
    assert "Test figure" in prompt
EOF
```

**Step 2: Run test to verify it fails**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_summarizer_with_images.py -v
```

Expected: FAIL with "has no attribute '_create_prompt_with_images_context'"

**Step 3: Write minimal implementation**

First, create the prompt template `prompts/image_analysis.md`:

```markdown
## Available Figures
{% for image in images %}
**Figure {{ loop.index }}** (Page {{ image.page_number }}):
- Type: {{ image.image_type }}
- Description: {{ image.analysis.description }}
- Key Findings: {{ image.analysis.key_findings | join(', ') }}
- Relevance: {{ image.analysis.relevance }}
{% endfor %}

When describing the paper's contributions, experiments, or results, reference specific figures by number when relevant.
```

Now modify `src/summarizer.py` to include image context:

```python
# Add new method to PaperSummarizer class
def _create_prompt_with_images_context(self, images: list) -> str:
    """Create image context section for prompt."""
    if not images:
        return ""

    context_parts = ["## Figures Analysis\n"]
    for i, img in enumerate(images, 1):
        if img.analysis:
            context_parts.append(f"**Figure {i}** (Page {img.page_number}):")
            context_parts.append(f"- {img.analysis.description}")
            if img.analysis.key_findings:
                context_parts.append(f"- Key findings: {', '.join(img.analysis.key_findings)}")
            context_parts.append("")

    return "\n".join(context_parts)

# Modify _create_prompt to include images
def _create_prompt(self, paper: Paper) -> str:
    """Create prompt from template."""
    template_name = f"summary_{self.language}.md"
    template_path = self.prompts_dir / template_name

    if not template_path.exists():
        template_path = self.prompts_dir / "summary_template.md"

    with template_path.open() as f:
        template = f.read()

    # Truncate text if too long
    max_chars = 15000
    text = paper.parsed_text[:max_chars] if paper.parsed_text else ""

    # NEW: Add image context if available
    images_context = ""
    if paper.images:
        analyzed_images = [img for img in paper.images if img.analysis]
        if analyzed_images:
            images_context = self._create_prompt_with_images_context(analyzed_images)

    return template.format(
        paper_title=paper.title,
        abstract=paper.abstract,
        full_text=text,
        language=self.language,
        summary_level=self.summary_level,
        images_context=images_context,  # NEW
    )
```

**Step 4: Run test to verify it passes**

```bash
cd /home/yuyuan/paper_daily && uv run pytest tests/unit/test_summarizer_with_images.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/yuyuan/paper_daily && git add src/summarizer.py prompts/image_analysis.md tests/unit/test_summarizer_with_images.py && git commit -m "feat: add image context to summarizer prompts"
```

---

## Phase 6: Dependencies and Configuration

### Task 7: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Run test to verify dependencies work**

```bash
cd /home/yuyuan/paper_daily && uv pip install pymupdf pillow anthropic
```

**Step 2: Verify installation**

```bash
cd /home/yuyuan/paper_daily && uv pip list | grep -E "pymupdf|pillow|anthropic"
```

**Step 3: Update pyproject.toml**

Edit `pyproject.toml` to add dependencies:

```toml
[project.dependencies]
# ... existing ...
pymupdf = ">=1.24.0"
pillow = ">=10.0.0"
anthropic = ">=0.40.0"
```

**Step 4: Commit**

```bash
cd /home/yuyuan/paper_daily && git add pyproject.toml && git commit -m "chore: add image processing dependencies"
```

---

## Phase 7: End-to-End Test

### Task 8: Run Full Integration Test

**Step 1: Create test configuration**

```bash
cat > config/test_vision.yaml << 'EOF'
query:
  keywords:
    - "large language model"
  max_results: 1

pipeline:
  language: zh
  summary_level: standard

vision:
  enabled: true
  extraction:
    min_size: [200, 200]
    max_aspect_ratio: 3.0
    max_images_per_paper: 5
    skip_duplicates: true
  analysis:
    provider: openai
    model_name: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
    batch_size: 2
    max_tokens: 500

model:
  provider: deepseek
  model_name: deepseek-chat
  api_key_env: DEEPSEEK_API_KEY
  temperature: 0.2
  max_tokens: 2000

output:
  base_dir: ./data

runtime:
  retry_times: 2
  timeout_sec: 60
  dry_run: false
EOF
```

**Step 2: Run the pipeline**

```bash
cd /home/yuyuan/paper_daily && OPENAI_API_KEY=$OPENAI_API_KEY DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY uv run python main.py --config config/test_vision.yaml
```

**Step 3: Verify output**

```bash
ls -la data/images/
ls -la data/summaries/
```

**Step 4: Commit**

```bash
cd /home/yuyuan/paper_daily && git add config/test_vision.yaml && git commit -m "test: add vision pipeline test configuration"
```

---

## Summary

This implementation adds image extraction and analysis to the paper pipeline:

| Phase | Task | Description |
|-------|------|-------------|
| 1 | 1-2 | Data models and configuration |
| 2 | 3 | ImageExtractor module |
| 3 | 4 | ImageAnalyzer module |
| 4 | 5 | Pipeline integration |
| 5 | 6 | Summary integration |
| 6 | 7 | Dependencies |
| 7 | 8 | End-to-end test |

Total: 8 tasks with TDD approach, each testable in 2-5 minutes.
