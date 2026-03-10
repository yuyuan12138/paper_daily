"""Tests for PDF parser module."""

from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
from models import Paper, PaperStatus
from parser import PDFParser


@pytest.mark.asyncio
async def test_parse_pdf_success():
    """Test successful PDF text extraction."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content\n\nPage 2 content"
        mock_reader.return_value.pages = [mock_page, mock_page]

        result = await parser.parse(paper)

    assert result.parsed_text is not None
    assert "Page 1 content" in result.parsed_text
    assert result.status == PaperStatus.parsed


@pytest.mark.asyncio
async def test_parse_pdf_cleans_text():
    """Test that parser cleans excessive whitespace."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Text  \n  \n  \nMore text   \n\n\n"
        mock_reader.return_value.pages = [mock_page]

        result = await parser.parse(paper)

    # Should collapse multiple blank lines
    assert "\n\n\n" not in result.parsed_text


@pytest.mark.asyncio
async def test_parse_pdf_missing_file():
    """Test handling when PDF file doesn't exist."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/nonexistent/2401.12345.pdf"),
    )

    result = await parser.parse(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_parse_pdf_encrypted():
    """Test handling encrypted/password-protected PDFs."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("parser.PdfReader") as mock_reader:
        mock_reader.side_effect = Exception("PDF is encrypted")

        result = await parser.parse(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_parse_empty_pdf():
    """Test handling PDF with no extractable text."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader.return_value.pages = [mock_page]

        result = await parser.parse(paper)

    # Should still succeed, just use abstract as text
    assert result.status == PaperStatus.parsed
    assert result.parsed_text == paper.abstract
