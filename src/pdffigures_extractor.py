"""PDFFigures2 extraction module for extracting figures from PDF papers."""

import asyncio
import json
import logging
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
                figures = data.get("figures", [])
                for fig_data in figures[:self.max_figures]:
                    metadata = self._process_figure(
                        fig_data, paper_output_dir, paper.arxiv_id
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
        cmd.extend([
            "java",
            "-jar",
            str(self.jar_path),
            str(pdf_path),
            "-i", str(temp_dir),
            "-d", str(self.dpi),
        ])

        # Add extraction options
        if self.extract_figures:
            cmd.append("-f")
        if self.extract_tables:
            cmd.append("-t")

        # Add max figures limit
        cmd.extend(["-m", str(self.max_figures)])

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
        self, fig_data: dict[str, Any], output_dir: Path, arxiv_id: str
    ) -> ImageMetadata | None:
        """Process a single figure from pdffigures2 output.

        This is a stub implementation that will be fully implemented in the next task.
        For now, it returns None to satisfy the interface.

        Args:
            fig_data: Figure data from pdffigures2 JSON output.
            output_dir: Directory to save extracted figures.
            arxiv_id: arXiv ID of the paper.

        Returns:
            ImageMetadata object, or None if processing failed.
        """
        # Stub implementation - will be fully implemented in next task
        return None
