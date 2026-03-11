"""State management for paper processing tracking."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from models import PaperStatus

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state for paper processing."""

    def __init__(self, state_file: Path | str):
        """Initialize state manager with state file path."""
        self.state_file = Path(state_file)
        self.state = {"last_run": None, "papers": {}}

    def load(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            with self.state_file.open() as f:
                self.state = json.load(f)

    def save(self) -> None:
        """Save state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_paper_status(self, arxiv_id: str) -> dict | None:
        """Get status entry for a paper."""
        return self.state["papers"].get(arxiv_id)

    def update_paper_status(
        self,
        arxiv_id: str,
        status: PaperStatus,
        pdf_path: Path | None = None,
        markdown_path: Path | None = None,
        error: str | None = None,
    ) -> None:
        """Update processing status for a paper.

        Optionally stores SHA256 hashes of files for integrity verification.
        """
        if arxiv_id not in self.state["papers"]:
            self.state["papers"][arxiv_id] = {}

        entry = self.state["papers"][arxiv_id]
        entry["status"] = status.value
        entry["updated_at"] = datetime.now().isoformat()

        # Store path and hash for PDF
        if pdf_path:
            entry["pdf_path"] = str(pdf_path)
            # Only calculate hash when file is first downloaded
            if "pdf_hash" not in entry or not Path(pdf_path).exists():
                entry["pdf_hash"] = self.get_file_hash(pdf_path)

        # Store path and hash for markdown
        if markdown_path:
            entry["markdown_path"] = str(markdown_path)
            entry["markdown_hash"] = self.get_file_hash(markdown_path)

        entry["error"] = error

    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if paper has been fully processed.

        Verifies:
        1. Status is 'summarized'
        2. Markdown file exists (if path is recorded)
        3. PDF file exists (if path is recorded)

        Returns False if any check fails, allowing reprocessing.
        """
        entry = self.get_paper_status(arxiv_id)
        if not entry:
            return False

        # Check status
        if entry["status"] != PaperStatus.summarized.value:
            return False

        # Check markdown file exists (if recorded)
        markdown_path = entry.get("markdown_path")
        if markdown_path and not Path(markdown_path).exists():
            logger.warning(f"Markdown file missing for {arxiv_id}: {markdown_path}")
            return False

        # Check PDF file exists (if recorded)
        pdf_path = entry.get("pdf_path")
        if pdf_path and not Path(pdf_path).exists():
            logger.warning(f"PDF file missing for {arxiv_id}: {pdf_path}")
            return False

        return True

    def get_papers_by_status(self, status: PaperStatus) -> list[str]:
        """Get all paper IDs with a given status."""
        return [
            arxiv_id
            for arxiv_id, entry in self.state["papers"].items()
            if entry["status"] == status.value
        ]

    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.state["last_run"] = datetime.now().isoformat()

    def invalidate_paper(self, arxiv_id: str) -> None:
        """Invalidate a paper's status, forcing reprocessing.

        Useful when files are manually deleted or corrupted.
        """
        if arxiv_id in self.state["papers"]:
            del self.state["papers"][arxiv_id]
            logger.info(f"Invalidated status for paper: {arxiv_id}")

    def cleanup_invalid_entries(self) -> dict:
        """Check all papers and remove entries with missing files.

        Returns:
            Dict with counts of cleaned entries by reason.
        """
        cleaned = {"missing_markdown": 0, "missing_pdf": 0, "total": 0}

        papers_to_remove = []
        for arxiv_id, entry in self.state["papers"].items():
            removed = False

            # Check markdown for summarized papers
            if entry.get("status") == PaperStatus.summarized.value:
                markdown_path = entry.get("markdown_path")
                if markdown_path and not Path(markdown_path).exists():
                    logger.warning(f"Cleaning up {arxiv_id}: missing markdown {markdown_path}")
                    cleaned["missing_markdown"] += 1
                    removed = True

            # Check PDF for papers with recorded path
            if not removed:
                pdf_path = entry.get("pdf_path")
                if pdf_path and not Path(pdf_path).exists():
                    logger.warning(f"Cleaning up {arxiv_id}: missing PDF {pdf_path}")
                    cleaned["missing_pdf"] += 1
                    removed = True

            if removed:
                papers_to_remove.append(arxiv_id)

        # Remove invalid entries
        for arxiv_id in papers_to_remove:
            del self.state["papers"][arxiv_id]

        cleaned["total"] = len(papers_to_remove)
        if cleaned["total"] > 0:
            logger.info(f"Cleaned {cleaned['total']} invalid entries")
            self.save()

        return cleaned

    @staticmethod
    def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str | None:
        """Calculate hash of a file.

        Args:
            file_path: Path to file.
            algorithm: Hash algorithm (sha256, md5, etc.)

        Returns:
            Hex digest of file hash, or None if file doesn't exist.
        """
        path = Path(file_path)
        if not path.exists():
            return None

        hash_func = hashlib.new(algorithm)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def verify_file_integrity(self, arxiv_id: str) -> dict:
        """Verify stored hash matches actual file.

        Returns:
            Dict with 'pdf_match' and 'markdown_match' boolean keys.
        """
        entry = self.get_paper_status(arxiv_id)
        if not entry:
            return {"error": "Paper not found in state"}

        result = {}

        # Check PDF
        pdf_path = entry.get("pdf_path")
        stored_pdf_hash = entry.get("pdf_hash")
        if pdf_path and stored_pdf_hash:
            actual_hash = self.get_file_hash(pdf_path)
            result["pdf_match"] = actual_hash == stored_pdf_hash
        else:
            result["pdf_match"] = None  # Not stored

        # Check markdown
        markdown_path = entry.get("markdown_path")
        stored_md_hash = entry.get("markdown_hash")
        if markdown_path and stored_md_hash:
            actual_hash = self.get_file_hash(markdown_path)
            result["markdown_match"] = actual_hash == stored_md_hash
        else:
            result["markdown_match"] = None  # Not stored

        return result
