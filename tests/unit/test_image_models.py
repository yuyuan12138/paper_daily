"""Tests for image metadata models."""

from datetime import datetime
from pathlib import Path
from models import Paper, PaperStatus, ImageMetadata, ImageAnalysis


def test_image_metadata_creation():
    """Test ImageMetadata can be created with required fields."""
    path = Path("/data/images/figure1.png")
    metadata = ImageMetadata(path=path, page_number=1)
    assert metadata.path == path
    assert metadata.page_number == 1
    assert metadata.figure_number is None
    assert metadata.caption is None
    assert metadata.analysis is None
    assert metadata.image_type == "unknown"


def test_image_metadata_with_optional_fields():
    """Test ImageMetadata with all optional fields."""
    path = Path("/data/images/figure1.png")
    analysis = ImageAnalysis(
        description="A bar chart showing results",
        key_findings=["Result A", "Result B"],
        relevance="high"
    )
    metadata = ImageMetadata(
        path=path,
        page_number=1,
        figure_number="Figure 1",
        caption="Experimental results comparison",
        analysis=analysis,
        image_type="chart"
    )
    assert metadata.path == path
    assert metadata.page_number == 1
    assert metadata.figure_number == "Figure 1"
    assert metadata.caption == "Experimental results comparison"
    assert metadata.analysis == analysis
    assert metadata.image_type == "chart"


def test_image_analysis_creation():
    """Test ImageAnalysis can be created."""
    analysis = ImageAnalysis(
        description="A neural network architecture diagram",
        key_findings=["Uses attention mechanism", "Has 3 layers"],
        relevance="high"
    )
    assert analysis.description == "A neural network architecture diagram"
    assert analysis.key_findings == ["Uses attention mechanism", "Has 3 layers"]
    assert analysis.relevance == "high"


def test_paper_status_includes_image_stages():
    """Test PaperStatus has the new enum values."""
    assert hasattr(PaperStatus, "images_extracted")
    assert hasattr(PaperStatus, "images_analyzed")
    assert PaperStatus.images_extracted.value == "images_extracted"
    assert PaperStatus.images_analyzed.value == "images_analyzed"


def test_paper_has_images_field():
    """Test Paper dataclass accepts images parameter."""
    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One"],
        abstract="Test abstract",
        submitted_date=datetime(2024, 1, 1),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )
    assert hasattr(paper, "images")
    assert paper.images == []

    # Test with images parameter
    image_metadata = ImageMetadata(path=Path("/data/image.png"), page_number=1)
    paper_with_images = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One"],
        abstract="Test abstract",
        submitted_date=datetime(2024, 1, 1),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        images=[image_metadata],
    )
    assert paper_with_images.images == [image_metadata]
