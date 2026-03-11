"""PDFFigures2 extraction module for extracting figures from PDF papers."""

import asyncio
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from models import Paper, PaperStatus, ImageMetadata

logger = logging.getLogger(__name__)


def _sanitize_arxiv_id(arxiv_id: str) -> str:
    """Sanitize arxiv_id to prevent path traversal attacks.

    Args:
        arxiv_id: The arxiv ID to sanitize.

    Returns:
        Sanitized arxiv ID with only allowed characters.
    """
    # Only allow alphanumeric characters, dots, and dashes
    return "".join(c for c in arxiv_id if c.isalnum() or c in ".-")


class PDFFigures2Extractor:
    """Extracts figures from PDF papers using pdffigures2 JAR."""

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
        """Initialize the PDFFigures2 extractor.

        Args:
            jar_path: Path to the pdffigures2 JAR file.
            output_dir: Directory to save extracted figures.
            dpi: DPI for figure extraction (default: 150).
            extract_figures: Whether to extract figures (default: True).
            extract_tables: Whether to extract tables (default: True).
            max_figures: Maximum number of figures to extract (default: 20).
            java_options: Optional list of Java JVM options (e.g., ["-Xmx2g"]).
        """
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.dpi = dpi
        self.extract_figures = extract_figures
        self.extract_tables = extract_tables
        self.max_figures = max_figures
        self.java_options = java_options

    async def extract(self, paper: Paper) -> Paper:
        """Extract figures from a paper's PDF using pdffigures2.

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        # Check if PDF path exists
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            # Run the blocking extraction in a thread pool
            return await asyncio.to_thread(self._extract_sync, paper)
        except Exception:
            logger.exception("Failed to extract figures from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _extract_sync(self, paper: Paper) -> Paper:
        """Synchronous figure extraction using pdffigures2 (runs in thread pool).

        Args:
            paper: The paper to extract figures from.

        Returns:
            The paper with extracted figures metadata.
        """
        # Check if JAR file exists
        if not self.jar_path.exists():
            logger.error("pdffigures2 JAR not found at: %s", self.jar_path)
            paper.status = PaperStatus.failed
            return paper

        try:
            # Create output directory for this paper
            paper_output_dir = self.output_dir / _sanitize_arxiv_id(paper.arxiv_id)
            paper_output_dir.mkdir(parents=True, exist_ok=True)

            # Create temporary directory for pdffigures2 output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Build command
                cmd = self._build_command(paper.pdf_path, temp_path)

                # Run pdffigures2
                logger.info("Running pdffigures2 for paper %s", paper.arxiv_id)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                )

                if result.returncode != 0:
                    logger.error(
                        "pdffigures2 failed for paper %s: %s",
                        paper.arxiv_id,
                        result.stderr,
                    )
                    paper.status = PaperStatus.failed
                    return paper

                # Find JSON output file
                json_file = self._find_json_output(temp_path)
                if not json_file:
                    logger.warning("No JSON output found for paper %s", paper.arxiv_id)
                    paper.status = PaperStatus.images_extracted
                    return paper

                # Parse JSON output
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Process each figure
                # pdffigures2 JSON is a list directly, not a dict with "figures" key
                figures = data if isinstance(data, list) else data.get("figures", [])
                for fig_data in figures[:self.max_figures]:
                    metadata = self._process_figure(
                        fig_data, paper_output_dir, paper.arxiv_id, temp_path
                    )
                    if metadata:
                        paper.images.append(metadata)

            # Update paper status
            if len(paper.images) > 0:
                paper.status = PaperStatus.images_extracted
            else:
                # Even if no figures found, mark as extracted (not failed)
                paper.status = PaperStatus.images_extracted

            return paper

        except subprocess.TimeoutExpired:
            logger.error("pdffigures2 timeout for paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper
        except Exception:
            logger.exception("Failed to extract figures from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _build_command(self, pdf_path: Path, temp_dir: Path) -> list[str]:
        """Build the command to run pdffigures2.

        Args:
            pdf_path: Path to the PDF file.
            temp_dir: Temporary directory for pdffigures2 output.

        Returns:
            List of command arguments.
        """
        cmd = []

        # Add Java options if provided
        if self.java_options:
            cmd.extend(self.java_options)

        # Build base command
        # Note: pdffigures2 CLI flags:
        # -i <value> : DPI to save figures (default 150)
        # -d <value> : figure-data-prefix for JSON output
        # -m <value> : figure-prefix for image output
        # -f <value> : figure format (default png)
        cmd.extend([
            "java",
            "-jar",
            str(self.jar_path),
            str(pdf_path),
            "-i", str(self.dpi),
            "-d", str(temp_dir / "data_output"),
            "-m", str(temp_dir / "figures_output"),
        ])

        return cmd

    def _find_json_output(self, temp_dir: Path) -> Path | None:
        """Find the JSON output file from pdffigures2.

        Args:
            temp_dir: Temporary directory containing pdffigures2 output.

        Returns:
            Path to the JSON file, or None if not found.
        """
        # Look for JSON files in temp directory
        json_files = list(temp_dir.glob("*.json"))
        if json_files:
            return json_files[0]
        return None

    def _process_figure(
        self,
        fig_data: dict[str, Any],
        output_dir: Path,
        arxiv_id: str,
        temp_dir: Path,
    ) -> ImageMetadata | None:
        """Process a single figure from pdffigures2 output.

        Args:
            fig_data: Figure data from pdffigures2 JSON output.
            output_dir: Directory to save extracted figures.
            arxiv_id: arXiv ID of the paper.
            temp_dir: Temporary directory containing pdffigures2 output.

        Returns:
            ImageMetadata object, or None if processing failed.
        """
        # Get figure type
        fig_type = fig_data.get("figType")
        if fig_type not in ["Figure", "Table"]:
            return None

        # Filter by extraction settings
        if fig_type == "Figure" and not self.extract_figures:
            return None
        if fig_type == "Table" and not self.extract_tables:
            return None

        # Get figure name
        fig_name = fig_data.get("name", "")
        if not fig_name:
            return None

        # Check if renderURL is provided in JSON data
        render_url = fig_data.get("renderURL", "")
        if render_url:
            # Use the renderURL to find the image file
            original_image = temp_dir / render_url
            if not original_image.exists():
                logger.warning(
                    "Could not find image file from renderURL: %s",
                    original_image,
                )
                return None
        else:
            # Fallback to pattern matching
            # pdffigures2 naming: figures_output{pdf_filename}-{figType}{name}-{index}.png
            # We need to find any file matching this pattern
            pattern = f"figures_output*-{fig_type}{fig_name}-*.png"
            matching_files = list(temp_dir.glob(pattern))

            if not matching_files:
                # Try alternative pattern without index
                pattern = f"figures_output*-{fig_type}{fig_name}.png"
                matching_files = list(temp_dir.glob(pattern))

            if not matching_files:
                logger.warning(
                    "Could not find image file for %s %s in paper %s",
                    fig_type,
                    fig_name,
                    arxiv_id,
                )
                return None

            # Use the first matching file
            original_image = matching_files[0]

        # Generate new filename: {fig_type}{fig_name}.png (e.g., Figure1.png, Table1.png)
        new_filename = f"{fig_type}{fig_name}.png"
        new_path = output_dir / new_filename

        # Copy image from temp_dir to output_dir with new name
        try:
            import shutil
            shutil.copy2(original_image, new_path)
        except Exception as e:
            logger.error(
                "Failed to copy image from %s to %s: %s",
                original_image,
                new_path,
                e,
            )
            return None

        # Parse caption - remove figure number prefix like "Figure 1:" or "Table 1:"
        caption = fig_data.get("caption", "")
        if caption:
            # Remove prefix pattern (case-insensitive)
            caption = re.sub(
                rf"^{fig_type}\s+{fig_name}:\s*", "", caption, flags=re.IGNORECASE
            )

        # Get page number (convert 0-based to 1-based)
        page = fig_data.get("page", 0)
        page_number = page + 1

        # Create and return ImageMetadata
        return ImageMetadata(
            path=new_path,
            page_number=page_number,
            figure_number=fig_name,
            caption=caption if caption else None,
            fig_type=fig_type,
            image_type=fig_type.lower(),
        )
