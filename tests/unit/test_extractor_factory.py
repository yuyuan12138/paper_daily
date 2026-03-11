"""Tests for ExtractorFactory class."""

from pathlib import Path
import tempfile

import pytest

from extractor_factory import ExtractorFactory
from image_extractor import ImageExtractor
from pdffigures_extractor import PDFFigures2Extractor
from config import VisionConfig


@pytest.fixture
def mock_jar_path():
    """Create a temporary mock JAR file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
        # Write some dummy content
        f.write(b"mock jar content")
        return Path(f.name)


@pytest.fixture
def output_dir():
    """Create a temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return Path(tmpdir)


class TestExtractorFactory:
    """Tests for the ExtractorFactory class."""

    def test_factory_creates_pymupdf_extractor(self, output_dir):
        """Test factory creates ImageExtractor when extractor is 'pymupdf'."""
        config = {
            "extractor": "pymupdf",
            "extraction": {
                "min_size": (150, 150),
                "max_aspect_ratio": 2.5,
                "max_images_per_paper": 15,
                "skip_duplicates": False,
            }
        }

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, ImageExtractor)
        assert extractor.min_size == (150, 150)
        assert extractor.max_aspect_ratio == 2.5
        assert extractor.max_images_per_paper == 15
        assert extractor.skip_duplicates is False
        assert extractor.output_dir == output_dir

    def test_factory_creates_pymupdf_extractor_with_vision_config(self, output_dir):
        """Test factory creates ImageExtractor when passed VisionConfig with 'pymupdf'."""
        config = VisionConfig(
            extractor="pymupdf",
            extraction={
                "min_size": (180, 180),
                "max_aspect_ratio": 2.8,
                "max_images_per_paper": 18,
                "skip_duplicates": True,
            }
        )

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, ImageExtractor)
        assert extractor.min_size == (180, 180)
        assert extractor.max_aspect_ratio == 2.8
        assert extractor.max_images_per_paper == 18
        assert extractor.skip_duplicates is True
        assert extractor.output_dir == output_dir

    def test_factory_creates_pdffigures2_extractor(self, output_dir, mock_jar_path):
        """Test factory creates PDFFigures2Extractor when extractor is 'pdffigures2'."""
        config = {
            "extractor": "pdffigures2",
            "pdffigures2_jar": str(mock_jar_path),
            "pdffigures2_dpi": 200,
            "pdffigures2_extract_figures": True,
            "pdffigures2_extract_tables": False,
            "pdffigures2_max_figures": 15,
        }

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, PDFFigures2Extractor)
        assert extractor.jar_path == mock_jar_path
        assert extractor.dpi == 200
        assert extractor.extract_figures is True
        assert extractor.extract_tables is False
        assert extractor.max_figures == 15
        assert extractor.output_dir == output_dir

    def test_factory_creates_pdffigures2_extractor_with_vision_config(self, output_dir, mock_jar_path):
        """Test factory creates PDFFigures2Extractor when passed VisionConfig with 'pdffigures2'."""
        config = VisionConfig(
            extractor="pdffigures2",
            pdffigures2_jar=str(mock_jar_path),
            pdffigures2_dpi=180,
            pdffigures2_extract_figures=True,
            pdffigures2_extract_tables=True,
            pdffigures2_max_figures=12,
        )

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, PDFFigures2Extractor)
        assert extractor.jar_path == mock_jar_path
        assert extractor.dpi == 180
        assert extractor.extract_figures is True
        assert extractor.extract_tables is True
        assert extractor.max_figures == 12
        assert extractor.output_dir == output_dir

    def test_factory_defaults_to_pymupdf(self, output_dir):
        """Test factory defaults to pymupdf when extractor not specified."""
        config = {
            "extraction": {
                "min_size": (200, 200),
            }
        }

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, ImageExtractor)
        assert extractor.min_size == (200, 200)

    def test_factory_defaults_to_pymupdf_with_empty_config(self, output_dir):
        """Test factory defaults to pymupdf with empty config."""
        config = {}

        extractor = ExtractorFactory.create(config, output_dir)

        assert isinstance(extractor, ImageExtractor)

    def test_factory_raises_value_error_for_pdffigures2_without_jar(self, output_dir):
        """Test factory raises ValueError when pdffigures2 selected but jar_path not configured."""
        config = {
            "extractor": "pdffigures2",
        }

        with pytest.raises(ValueError) as exc_info:
            ExtractorFactory.create(config, output_dir)

        assert "pdffigures2_jar" in str(exc_info.value)
        assert "must be configured" in str(exc_info.value)

    def test_factory_raises_value_error_for_pdffigures2_with_none_jar(self, output_dir):
        """Test factory raises ValueError when pdffigures2 selected but jar_path is None."""
        config = {
            "extractor": "pdffigures2",
            "pdffigures2_jar": None,
        }

        with pytest.raises(ValueError) as exc_info:
            ExtractorFactory.create(config, output_dir)

        assert "pdffigures2_jar" in str(exc_info.value)
