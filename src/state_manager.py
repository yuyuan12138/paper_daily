"""State management for paper processing tracking."""

from datetime import datetime
from pathlib import Path
import json
from models import PaperStatus


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
        """Update processing status for a paper."""
        if arxiv_id not in self.state["papers"]:
            self.state["papers"][arxiv_id] = {}

        entry = self.state["papers"][arxiv_id]
        entry["status"] = status.value
        entry["updated_at"] = datetime.now().isoformat()

        if pdf_path:
            entry["pdf_path"] = str(pdf_path)
        if markdown_path:
            entry["markdown_path"] = str(markdown_path)
        entry["error"] = error

    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if paper has been fully processed."""
        entry = self.get_paper_status(arxiv_id)
        if not entry:
            return False
        return entry["status"] == PaperStatus.summarized.value

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
