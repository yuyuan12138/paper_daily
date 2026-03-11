"""Integration tests for pdffigures2 extraction."""

import pytest
from pathlib import Path
from datetime import datetime

from pdffigures_extractor import PDFFigures2Extractor
from models import Paper, PaperStatus


@pytest.fixture
def real_pdf(tmp_path):
    """Use a real PDF from test data."""
    pdf_path = Path("tests/fixtures/sample.pdf")
    if not pdf_path.exists():
        pytest.skip("Test PDF not found")
    return pdf_path


@pytest.fixture
def jar_path():
    """Path to compiled pdffigures2 assembly JAR."""
    jar = Path("pdffigures2/pdffigures2.jar")
    if not jar.exists():
        pytest.skip(
            "pdffigures2 assembly JAR not found. Run: cd pdffigures2 && sbt assembly"
        )
    return jar


def test_extract_from_real_pdf(real_pdf, jar_path, tmp_path):
    """Test extraction from a real PDF file."""
    extractor = PDFFigures2Extractor(
        jar_path=jar_path,
        output_dir=tmp_path / "output",
    )

    paper = Paper(
        arxiv_id="2603.08486",
        title="Sample Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2603.08486.pdf",
        pdf_path=real_pdf,
    )

    result = extractor._extract_sync(paper)

    assert result.status == PaperStatus.images_extracted
    assert len(result.images) > 0

    first_image = result.images[0]
    assert first_image.path.exists()
    assert first_image.fig_type in ["Figure", "Table"]
    assert first_image.page_number > 0
    assert first_image.image_type in ["figure", "table"]


def test_extract_with_jar_not_found(real_pdf, tmp_path):
    """Test that extraction handles missing JAR gracefully."""
    extractor = PDFFigures2Extractor(
        jar_path=tmp_path / "nonexistent.jar",
        output_dir=tmp_path / "output",
    )

    paper = Paper(
        arxiv_id="test-sample",
        title="Sample Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/test.pdf",
        pdf_path=real_pdf,
    )

    result = extractor._extract_sync(paper)

    # Should fail gracefully when JAR is not found
    assert result.status == PaperStatus.failed
    assert len(result.images) == 0


def test_extract_with_pdf_not_found(jar_path, tmp_path):
    """Test that extraction handles missing PDF gracefully."""
    extractor = PDFFigures2Extractor(
        jar_path=jar_path,
        output_dir=tmp_path / "output",
    )

    paper = Paper(
        arxiv_id="test-sample",
        title="Sample Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/test.pdf",
        pdf_path=tmp_path / "nonexistent.pdf",
    )

    result = extractor._extract_sync(paper)

    # Should fail gracefully when PDF is not found
    assert result.status == PaperStatus.failed
    assert len(result.images) == 0


def test_extract_metadata_quality(real_pdf, jar_path, tmp_path):
    """Test that extracted metadata has expected quality."""
    extractor = PDFFigures2Extractor(
        jar_path=jar_path,
        output_dir=tmp_path / "output",
        dpi=150,
        extract_figures=True,
        extract_tables=True,
    )

    paper = Paper(
        arxiv_id="2603.08486",
        title="Sample Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2603.08486.pdf",
        pdf_path=real_pdf,
    )

    result = extractor._extract_sync(paper)

    assert result.status == PaperStatus.images_extracted
    assert len(result.images) > 0

    # Check that all images have required metadata
    for img in result.images:
        assert img.path.exists()
        assert img.page_number > 0
        assert img.fig_type in ["Figure", "Table"]
        assert img.image_type in ["figure", "table"]
        assert img.path.suffix == ".png"

        # Check that caption was extracted (even if empty)
        assert img.caption is None or isinstance(img.caption, str)

        # Check that figure_number was extracted
        assert img.figure_number is not None
        assert len(img.figure_number) > 0
