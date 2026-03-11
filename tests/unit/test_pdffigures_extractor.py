"""Tests for PDFFigures2Extractor class."""

from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from models import Paper, PaperStatus, ImageMetadata
from pdffigures_extractor import PDFFigures2Extractor


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

    def test_extractor_init_with_java_options(self, mock_jar_path):
        """Test PDFFigures2Extractor initialization with custom Java options."""
        java_opts = ["-Xmx2g", "-Dfile.encoding=UTF-8"]
        extractor = PDFFigures2Extractor(
            jar_path=mock_jar_path,
            output_dir=Path("/tmp/output"),
            java_options=java_opts,
        )

        assert extractor.java_options == java_opts

    def test_build_command_basic(self, extractor, mock_jar_path):
        """Test _build_command creates basic command structure."""
        pdf_path = Path("/tmp/test.pdf")
        temp_dir = Path("/tmp/temp_extraction")

        cmd = extractor._build_command(pdf_path, temp_dir)

        # Check command structure
        assert "java" in cmd
        assert "-jar" in cmd
        assert str(mock_jar_path) in cmd
        assert str(pdf_path) in cmd
        assert "-i" in cmd
        assert str(temp_dir) in cmd

    def test_build_command_with_dpi(self, extractor, mock_jar_path):
        """Test _build_command includes DPI setting."""
        pdf_path = Path("/tmp/test.pdf")
        temp_dir = Path("/tmp/temp_extraction")

        cmd = extractor._build_command(pdf_path, temp_dir)

        # Check DPI is included
        assert "-d" in cmd
        assert "200" in cmd  # Our custom DPI value

    def test_build_command_with_figure_options(self, extractor, mock_jar_path):
        """Test _build_command includes figure/table extraction options."""
        pdf_path = Path("/tmp/test.pdf")
        temp_dir = Path("/tmp/temp_extraction")

        cmd = extractor._build_command(pdf_path, temp_dir)

        # Check extraction flags
        assert "-f" in cmd  # extract_figures
        assert "-t" in cmd  # extract_tables

    def test_build_command_with_max_figures(self, extractor, mock_jar_path):
        """Test _build_command includes max figures limit."""
        pdf_path = Path("/tmp/test.pdf")
        temp_dir = Path("/tmp/temp_extraction")

        cmd = extractor._build_command(pdf_path, temp_dir)

        # Check max figures is included
        assert "-m" in cmd
        assert "15" in cmd  # Our custom max_figures value

    def test_build_command_with_java_options(self, mock_jar_path):
        """Test _build_command includes custom Java options."""
        java_opts = ["-Xmx4g", "-Dfile.encoding=UTF-8"]
        extractor = PDFFigures2Extractor(
            jar_path=mock_jar_path,
            output_dir=Path("/tmp/output"),
            java_options=java_opts,
        )

        pdf_path = Path("/tmp/test.pdf")
        temp_dir = Path("/tmp/temp_extraction")

        cmd = extractor._build_command(pdf_path, temp_dir)

        # Check Java options are included at the start
        assert "-Xmx4g" in cmd
        assert "-Dfile.encoding=UTF-8" in cmd
        # Java options should come before -jar
        assert cmd.index("-Xmx4g") < cmd.index("-jar")

    def test_find_json_output_no_files(self, extractor, tmp_path):
        """Test _find_json_output returns None when no JSON files exist."""
        result = extractor._find_json_output(tmp_path)
        assert result is None

    def test_find_json_output_with_files(self, extractor, tmp_path):
        """Test _find_json_output finds JSON output file."""
        # Create a mock JSON file
        json_file = tmp_path / "figures.json"
        json_file.write_text('{"figures": []}')

        result = extractor._find_json_output(tmp_path)
        assert result == json_file

    def test_process_figure_stub(self, extractor):
        """Test _process_figure returns None (stub implementation)."""
        # This is a stub that will be fully implemented in the next task
        fig_data = {
            "figType": "Figure",
            "caption": "Test caption",
            "page": 1,
        }

        result = extractor._process_figure(
            fig_data=fig_data,
            output_dir=Path("/tmp/output"),
            arxiv_id="2401.12345",
        )

        # Stub should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_no_pdf_path(self, extractor):
        """Test extract handles missing PDF path."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author"],
            abstract="Test abstract",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            # pdf_path is None
        )

        result = await extractor.extract(paper)

        assert result.status == PaperStatus.failed

    @pytest.mark.asyncio
    async def test_extract_with_pdf_path(self, extractor):
        """Test extract with PDF path (integration test skeleton)."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author"],
            abstract="Test abstract",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            pdf_path=Path("/tmp/nonexistent.pdf"),  # File doesn't exist
        )

        # This will fail because PDF doesn't exist, but tests the flow
        result = await extractor.extract(paper)

        # Should handle gracefully
        assert result.status in [PaperStatus.failed, PaperStatus.images_extracted]
