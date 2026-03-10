"""Core data models for the paper pipeline."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class PaperStatus(Enum):
    """Processing status of a paper in the pipeline."""

    discovered = "discovered"  # Retrieved from arXiv
    downloaded = "downloaded"  # PDF saved locally
    parsed = "parsed"  # Text extracted
    summarized = "summarized"  # LLM summary complete
    images_extracted = "images_extracted"  # Images extracted from PDF
    images_analyzed = "images_analyzed"  # Image analysis complete
    failed = "failed"  # Error at any stage


@dataclass
class ImageAnalysis:
    """Analysis results for an image extracted from a paper."""

    description: str
    key_findings: list[str]
    relevance: str  # "high" | "medium" | "low"


@dataclass
class ImageMetadata:
    """Metadata for an image extracted from a paper."""

    path: Path
    page_number: int
    figure_number: str | None = None
    caption: str | None = None
    analysis: ImageAnalysis | None = None
    image_type: str = "unknown"


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
    summary: dict[str, Any] | None = None
    images: list[ImageMetadata] = None
    status: PaperStatus = PaperStatus.discovered

    def __post_init__(self):
        if self.images is None:
            self.images = []


__all__ = ["Paper", "PaperStatus", "ImageMetadata", "ImageAnalysis"]
