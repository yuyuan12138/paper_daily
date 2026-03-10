"""ArXiv paper fetcher using the arxiv library."""

import re
from datetime import datetime
from typing import Self

import arxiv

from config import QueryConfig
from models import Paper, PaperStatus


class ArXivFetcher:
    """Fetches paper metadata from arXiv."""

    def __init__(self, config: QueryConfig) -> None:
        """Initialize fetcher with query configuration."""
        self.config = config

    async def fetch(self) -> list[Paper]:
        """Fetch papers from arXiv based on configuration."""
        # Build query string
        query_parts = []
        for keyword in self.config.keywords:
            query_parts.append(f'all:"{keyword}"')
        for category in self.config.categories:
            query_parts.append(f"cat:{category}")

        query_str = " OR ".join(query_parts) if query_parts else "all:*"

        # Create search
        search = arxiv.Search(
            query=query_str,
            max_results=self.config.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=(
                arxiv.SortOrder.Descending
                if self.config.sort_order == "descending"
                else arxiv.SortOrder.Ascending
            ),
        )

        papers = []
        with arxiv.Client() as client:
            for result in client.results(search):
                paper = Paper(
                    arxiv_id=self._extract_arxiv_id(result.entry_id),
                    title=result.title,
                    authors=[a.name for a in result.authors],
                    abstract=result.summary.replace("\n", " ").strip(),
                    submitted_date=result.published,
                    categories=result.categories,
                    pdf_url=result.pdf_url,
                    status=PaperStatus.discovered,
                )
                papers.append(paper)

        return papers

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """Extract arXiv ID from entry ID or URL."""
        # Match patterns like "2401.12345v1" or "2401.12345"
        match = re.search(r"(\d{4}\.\d+)", entry_id)
        if match:
            return match.group(1)
        # Fallback: return as-is if pattern doesn't match
        return entry_id.split("v")[0] if "v" in entry_id else entry_id
