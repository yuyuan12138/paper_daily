"""PDF downloader module with retry logic."""

import asyncio
from pathlib import Path

import httpx
from httpx import HTTPStatusError, TimeoutException

from models import Paper, PaperStatus


class PDFDownloader:
    """Downloads PDF files from arXiv."""

    def __init__(
        self,
        base_dir: Path,
        retry_times: int = 3,
        timeout_sec: int = 60,
    ) -> None:
        """Initialize downloader with configuration."""
        self.base_dir = base_dir
        self.retry_times = retry_times
        self.timeout_sec = timeout_sec
        self.pdf_dir = base_dir / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, paper: Paper) -> Paper:
        """Download PDF for a paper."""
        pdf_path = self.pdf_dir / f"{paper.arxiv_id}.pdf"

        # Skip if already exists
        if pdf_path.exists():
            paper.pdf_path = pdf_path
            paper.status = PaperStatus.downloaded
            return paper

        # Download with retry
        for attempt in range(self.retry_times + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    async with client.stream("GET", paper.pdf_url) as response:
                        response.raise_for_status()
                        content = await response.aread()
                        pdf_path.write_bytes(content)

                paper.pdf_path = pdf_path
                paper.status = PaperStatus.downloaded
                return paper

            except TimeoutException:
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    paper.status = PaperStatus.failed
                    return paper

            except HTTPStatusError as e:
                if e.response.status_code in (404, 403):
                    # Don't retry client errors
                    paper.status = PaperStatus.failed
                    return paper
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)
                else:
                    paper.status = PaperStatus.failed
                    return paper

            except Exception:
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)
                else:
                    paper.status = PaperStatus.failed
                    return paper

        paper.status = PaperStatus.failed
        return paper
