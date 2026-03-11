"""Tests for PDFFigures2Extractor class."""

from pathlib import Path
import tempfile

import pytest

from pdffigures_extractor import PDFFigures2Extractor
from models import ImageMetadata, Paper, PaperStatus
from datetime import datetime


@pytest.fixture
def mock_jar_path():
    """Create a temporary mock JAR file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
        # Write some dummy content
        f.write(b"mock jar content")
        return Path(f.name)


@pytest.fixture
def extractor(mock_jar_path):
    """Create a PDFFigures2Extractor instance for testing."""
    output_dir = Path("/tmp/test_output")
    return PDFFigures2Extractor(
        jar_path=mock_jar_path,
        output_dir=output_dir,
        dpi=200,
        extract_figures=True,
        extract_tables=True,
        max_figures=15,
    )


class TestPDFFigures2Extractor:
    """Tests for the PDFFigures2Extractor class."""

    def test_extractor_init(self, extractor, mock_jar_path):
        """Test PDFFigures2Extractor initialization with custom parameters."""
        assert extractor.jar_path == mock_jar_path
        assert extractor.output_dir == Path("/tmp/test_output")
        assert extractor.dpi == 200
        assert extractor.extract_figures is True
        assert extractor.extract_tables is True
        assert extractor.max_figures == 15
        assert extractor.java_options is None

    def test_extractor_init_with_defaults(self, mock_jar_path):
        """Test PDFFigures2Extractor initialization with default parameters."""
        extractor = PDFFigures2Extractor(
            jar_path=mock_jar_path,
            output_dir=Path("/tmp/default_output"),
        )

        assert extractor.jar_path == mock_jar_path
        assert extractor.output_dir == Path("/tmp/default_output")
        assert extractor.dpi == 150  # Default value
        assert extractor.extract_figures is True  # Default value
        assert extractor.extract_tables is True  # Default value
        assert extractor.max_figures == 20  # Default value
        assert extractor.java_options is None  # Default value

    def test_process_figure_renames_image(self, extractor, tmp_path):
        """Test that _process_figure renames and copies image correctly."""
        # Create a temporary directory with a mock image file
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a mock image file with pdffigures2 naming convention
        mock_image = temp_dir / "test-paper-Figure1-1.png"
        mock_image.write_bytes(b"fake image data")

        # Mock figure data from pdffigures2 JSON output
        fig_data = {
            "figType": "Figure",
            "name": "1",
            "caption": "Figure 1: A test figure with description",
            "page": 0,  # 0-based page number
        }

        # Process the figure
        result = extractor._process_figure(
            fig_data, output_dir, "test-paper", temp_dir
        )

        # Verify the result
        assert isinstance(result, ImageMetadata)
        assert result.fig_type == "Figure"
        assert result.figure_number == "1"
        assert result.caption == "A test figure with description"  # Figure number prefix removed
        assert result.page_number == 1  # Converted to 1-based
        assert result.path == output_dir / "Figure1.png"
        assert result.path.exists()
        assert result.path.read_bytes() == b"fake image data"

    def test_process_figure_filters_by_type(self, extractor, tmp_path):
        """Test that _process_figure filters by extract_figures/extract_tables settings."""
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create extractor that only extracts figures, not tables
        figures_only_extractor = PDFFigures2Extractor(
            jar_path=extractor.jar_path,
            output_dir=output_dir,
            extract_figures=True,
            extract_tables=False,
        )

        # Test with a table - should be filtered out
        table_data = {
            "figType": "Table",
            "name": "1",
            "caption": "Table 1: Test table",
            "page": 0,
        }
        mock_table_image = temp_dir / "test-paper-Table1-1.png"
        mock_table_image.write_bytes(b"table data")

        result = figures_only_extractor._process_figure(
            table_data, output_dir, "test-paper", temp_dir
        )
        assert result is None  # Should be filtered out

        # Test with a figure - should be processed
        figure_data = {
            "figType": "Figure",
            "name": "1",
            "caption": "Figure 1: Test figure",
            "page": 0,
        }
        mock_figure_image = temp_dir / "test-paper-Figure1-1.png"
        mock_figure_image.write_bytes(b"figure data")

        result = figures_only_extractor._process_figure(
            figure_data, output_dir, "test-paper", temp_dir
        )
        assert isinstance(result, ImageMetadata)
        assert result.fig_type == "Figure"

    def test_process_figure_handles_missing_image(self, extractor, tmp_path):
        """Test that _process_figure returns None when image file is missing."""
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock figure data but don't create the image file
        fig_data = {
            "figType": "Figure",
            "name": "1",
            "caption": "Figure 1: Test",
            "page": 0,
        }

        result = extractor._process_figure(
            fig_data, output_dir, "test-paper", temp_dir
        )
        assert result is None

    def test_extract_with_missing_jar(self, tmp_path):
        """Test that extraction fails gracefully when JAR file doesn't exist."""
        # Create extractor with nonexistent JAR path
        nonexistent_jar = tmp_path / "nonexistent" / "pdffigures2.jar"
        output_dir = tmp_path / "output"
        extractor = PDFFigures2Extractor(
            jar_path=nonexistent_jar,
            output_dir=output_dir,
        )

        # Create a mock paper with a PDF path
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")
        paper = Paper(
            arxiv_id="1234.5678",
            title="Test Paper",
            authors=["Test Author"],
            abstract="Test abstract",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
            pdf_path=pdf_path,
        )

        # Call _extract_sync() on the paper
        result = extractor._extract_sync(paper)

        # Assert paper.status == PaperStatus.failed
        assert result.status == PaperStatus.failed
