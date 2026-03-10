from datetime import datetime
from pathlib import Path
from models import Paper, PaperStatus


def test_paper_creation():
    """Test creating a Paper object with required fields."""
    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One", "Author Two"],
        abstract="This is a test abstract.",
        submitted_date=datetime(2024, 1, 1, 12, 0, 0),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )
    assert paper.arxiv_id == "2401.12345"
    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.status == PaperStatus.discovered
    assert paper.pdf_path is None
    assert paper.parsed_text is None
    assert paper.summary is None


def test_paper_status_enum():
    """Test PaperStatus enum values."""
    assert PaperStatus.discovered.value == "discovered"
    assert PaperStatus.downloaded.value == "downloaded"
    assert PaperStatus.parsed.value == "parsed"
    assert PaperStatus.summarized.value == "summarized"
    assert PaperStatus.failed.value == "failed"


def test_paper_with_optional_fields():
    """Test Paper object with optional fields populated."""
    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One"],
        abstract="Test abstract",
        submitted_date=datetime(2024, 1, 1),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
        parsed_text="Extracted text content",
        summary={"research_problem": "Test problem"},
        status=PaperStatus.summarized,
    )
    assert paper.pdf_path == Path("/data/pdfs/2401.12345.pdf")
    assert paper.parsed_text == "Extracted text content"
    assert paper.summary == {"research_problem": "Test problem"}
    assert paper.status == PaperStatus.summarized
