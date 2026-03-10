"""Tests for PDF downloader module."""

from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import HTTPStatusError, TimeoutException
from models import Paper, PaperStatus
from downloader import PDFDownloader


@pytest.mark.asyncio
async def test_download_pdf_success(tmp_path):
    """Test successful PDF download."""
    downloader = PDFDownloader(base_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    # Mock httpx async stream
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.aread.return_value = b"fake pdf content"

        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = mock_stream

        result = await downloader.download(paper)

    assert result.pdf_path is not None
    assert result.pdf_path.name == "2401.12345.pdf"
    assert result.status == PaperStatus.downloaded
    assert result.pdf_path.exists()


@pytest.mark.asyncio
async def test_download_skip_if_exists(tmp_path):
    """Test skipping download if PDF already exists."""
    downloader = PDFDownloader(base_dir=tmp_path)

    # Create existing PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    existing_pdf = pdf_dir / "2401.12345.pdf"
    existing_pdf.write_bytes(b"existing content")

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    result = await downloader.download(paper)

    assert result.pdf_path == existing_pdf
    assert result.status == PaperStatus.downloaded
    # Content should not change
    assert result.pdf_path.read_bytes() == b"existing content"


@pytest.mark.asyncio
async def test_download_with_retry_on_timeout():
    """Test retry behavior on timeout."""
    downloader = PDFDownloader(retry_times=2, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        # First call times out, second succeeds
        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.aread.return_value = b"pdf content"

        mock_client.return_value.__aenter__.return_value.stream.side_effect = [
            TimeoutException("Timeout"),
            mock_stream,
        ]

        result = await downloader.download(paper)

    assert result.status == PaperStatus.downloaded


@pytest.mark.asyncio
async def test_download_failure_after_retries():
    """Test marking as failed after max retries."""
    downloader = PDFDownloader(retry_times=1, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream.side_effect = TimeoutException("Timeout")

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_download_404_not_found():
    """Test handling 404 error without retry."""
    downloader = PDFDownloader(retry_times=3, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        response = MagicMock()
        response.status_code = 404

        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = response
        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.raise_for_status.side_effect = HTTPStatusError(
            "Not found", request=MagicMock(), response=response
        )

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed
