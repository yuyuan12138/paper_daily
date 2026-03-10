"""Core data models for the paper pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class PaperStatus(Enum):
    """Processing status of a paper in the pipeline."""

    discovered = "discovered"  # Retrieved from arXiv
    downloaded = "downloaded"  # PDF saved locally
    parsed = "parsed"  # Text extracted
    summarized = "summarized"  # LLM summary complete
    failed = "failed"  # Error at any stage


@dataclass
class Paper:
    """Represents a research paper from arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    submitted_date: datetime
    categories: list[str]
    pdf_url: str
    pdf_path: Path | None = None
    parsed_text: str | None = None
    summary: dict | None = None
    status: PaperStatus = PaperStatus.discovered
