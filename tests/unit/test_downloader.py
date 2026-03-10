"""Tests for PDF downloader module."""

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

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aread = AsyncMock(return_value=b"fake pdf content")
    mock_response.raise_for_status = MagicMock()

    # Create the async context manager mock
    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__.return_value = mock_response

    # Mock the stream method to return the context manager
    mock_client_instance = MagicMock()
    mock_client_instance.stream = MagicMock(return_value=mock_stream_context)

    with patch("downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_client_instance

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
async def test_download_with_retry_on_timeout(tmp_path):
    """Test retry behavior on timeout."""
    downloader = PDFDownloader(retry_times=2, base_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    call_count = [0]

    def stream_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call raises timeout
            raise TimeoutException("Timeout")
        # Second call succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aread = AsyncMock(return_value=b"pdf content")
        mock_response.raise_for_status = MagicMock()

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        return mock_stream_context

    mock_client_instance = MagicMock()
    mock_client_instance.stream = stream_side_effect

    with patch("downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await downloader.download(paper)

    assert result.status == PaperStatus.downloaded


@pytest.mark.asyncio
async def test_download_failure_after_retries(tmp_path):
    """Test marking as failed after max retries."""
    downloader = PDFDownloader(retry_times=1, base_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    def stream_side_effect(*args, **kwargs):
        raise TimeoutException("Timeout")

    mock_client_instance = MagicMock()
    mock_client_instance.stream = stream_side_effect

    with patch("downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_download_404_not_found(tmp_path):
    """Test handling 404 error without retry."""
    downloader = PDFDownloader(retry_times=3, base_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    response = MagicMock()
    response.status_code = 404

    def stream_side_effect(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 404

        def raise_for_status():
            raise HTTPStatusError("Not found", request=MagicMock(), response=response)

        mock_response.raise_for_status = raise_for_status

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        return mock_stream_context

    mock_client_instance = MagicMock()
    mock_client_instance.stream = stream_side_effect

    with patch("downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed
