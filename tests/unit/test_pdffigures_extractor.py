"""Tests for PDFFigures2Extractor class."""

from pathlib import Path
import tempfile

import pytest

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
