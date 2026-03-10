"""Tests for Markdown renderer module."""

from datetime import datetime
from pathlib import Path
import pytest
from models import Paper, PaperStatus
from renderer import MarkdownRenderer


def test_render_basic_markdown(tmp_path):
    """Test basic Markdown rendering."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper Title",
        authors=["Alice Smith", "Bob Jones"],
        abstract="This is a test abstract describing the paper.",
        submitted_date=datetime(2024, 1, 15, 10, 30, 0),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
        parsed_text="Full text content...",
        summary={
            "research_problem": "Test problem description",
            "core_method": "Test method description",
            "contributions": ["Contribution 1", "Contribution 2"],
            "experiments": "Test experiments description",
            "limitations": "Test limitations",
            "keywords": ["AI", "machine learning", "transformers"],
            "applicable_scenarios": "Test scenarios",
        },
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    assert output_path.exists()
    content = output_path.read_text()

    # Verify key sections
    assert "# Test Paper Title" in content
    assert "Alice Smith" in content
    assert "Bob Jones" in content
    assert "2401.12345" in content
    assert "This is a test abstract" in content
    assert "Test problem description" in content
    assert "Test method description" in content
    assert "Contribution 1" in content
    assert "machine learning" in content


def test_render_creates_directory(tmp_path):
    """Test that renderer creates output directory."""
    output_dir = tmp_path / "summaries"
    renderer = MarkdownRenderer(output_dir=output_dir)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test",
        authors=["A"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/test.pdf",
        summary={"research_problem": "Test"},
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    assert output_dir.exists()
    assert output_path.parent == output_dir


def test_render_without_summary(tmp_path):
    """Test rendering paper without summary."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        summary=None,
        status=PaperStatus.parsed,
    )

    output_path = renderer.render(paper)

    assert output_path.exists()
    content = output_path.read_text()
    assert "# Test Paper" in content
    assert "No summary available" in content


def test_render_sanitizes_filename(tmp_path):
    """Test that special characters in title are sanitized."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test/Paper: Special <Characters> & More!",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        summary={"research_problem": "Test"},
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    # Filename should not contain special characters
    assert "/" not in output_path.name
    assert ":" not in output_path.name
    assert "<" not in output_path.name
