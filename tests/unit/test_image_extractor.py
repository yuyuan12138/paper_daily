"""Tests for image extraction module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from models import Paper, PaperStatus, ImageMetadata
from image_extractor import ImageExtractor


class TestImageExtractor:
    """Tests for the ImageExtractor class."""

    def test_extractor_initialization(self):
        """Test ImageExtractor can be initialized with default parameters."""
        extractor = ImageExtractor()

        assert extractor.min_size == (200, 200)
        assert extractor.max_aspect_ratio == 3.0
        assert extractor.max_images_per_paper == 20
        assert extractor.skip_duplicates is True
        assert extractor.output_dir == Path("data/images")

    def test_extractor_initialization_custom(self):
        """Test ImageExtractor can be initialized with custom parameters."""
        output_dir = Path("custom/images")
        extractor = ImageExtractor(
            min_size=(100, 100),
            max_aspect_ratio=2.5,
            max_images_per_paper=10,
            skip_duplicates=False,
            output_dir=output_dir,
        )

        assert extractor.min_size == (100, 100)
        assert extractor.max_aspect_ratio == 2.5
        assert extractor.max_images_per_paper == 10
        assert extractor.skip_duplicates is False
        assert extractor.output_dir == output_dir

    def test_should_include_image_small(self):
        """Test _should_include_image filters small images."""
        extractor = ImageExtractor(min_size=(200, 200))

        # Image should be excluded if smaller than min_size
        assert extractor._should_include_image(100, 100, 0.5) is False
        assert extractor._should_include_image(199, 200, 0.5) is False
        assert extractor._should_include_image(200, 199, 0.5) is False

    def test_should_include_image_valid_size(self):
        """Test _should_include_image accepts valid size images."""
        extractor = ImageExtractor(min_size=(200, 200))

        # Image at min_size should be included
        assert extractor._should_include_image(200, 200, 0.5) is True

        # Larger images should be included
        assert extractor._should_include_image(500, 500, 0.5) is True

    def test_extractor_filters_aspect_ratio(self):
        """Test aspect ratio filtering."""
        extractor = ImageExtractor(max_aspect_ratio=3.0)

        # Aspect ratio within limit should be included
        # width/height = 2.0 (within 3.0)
        assert extractor._should_include_image(400, 200, 0.5) is True

        # width/height = 3.0 (at limit)
        assert extractor._should_include_image(600, 200, 0.5) is True

        # width/height > 3.0 should be excluded
        assert extractor._should_include_image(601, 200, 0.5) is False

        # Also test height > width (tall images)
        # height/width = 4.0 > 3.0
        assert extractor._should_include_image(100, 400, 0.5) is False

    def test_extractor_filters_header_footer(self):
        """Test position filtering for header/footer."""
        extractor = ImageExtractor()

        # Valid middle positions should be included
        assert extractor._should_include_image(500, 500, 0.5) is True
        assert extractor._should_include_image(500, 500, 0.1) is True
        assert extractor._should_include_image(500, 500, 0.9) is True
        assert extractor._should_include_image(500, 500, 0.15) is True
        assert extractor._should_include_image(500, 500, 0.85) is True

        # Header positions should be excluded (y < 0.1)
        assert extractor._should_include_image(500, 500, 0.05) is False
        assert extractor._should_include_image(500, 500, 0.09) is False

        # Footer positions should be excluded (y > 0.9)
        assert extractor._should_include_image(500, 500, 0.91) is False
        assert extractor._should_include_image(500, 500, 0.95) is False

    @pytest.mark.asyncio
    async def test_extract_no_pdf_path(self):
        """Test extract handles missing PDF path."""
        extractor = ImageExtractor()

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
    async def test_extract_updates_paper(self):
        """Test extract updates paper with images."""
        extractor = ImageExtractor(output_dir=Path("/tmp/test_images"))

        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author"],
            abstract="Test abstract",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            pdf_path=Path("/tmp/test.pdf"),
        )

        # Create a mock PDF
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect.y1 = 1000  # Page height

        # Mock image tuple (xref, width, height, ...)
        mock_image_tuple = (1, 3, 8, 0, 0, 500, 500, 0, "RGB", "")

        mock_page.get_images.return_value = [mock_image_tuple]
        mock_page.get_image_rects.return_value = [MagicMock(y0=300, y1=500)]

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        # Mock extract_image to return valid image data
        mock_image_data = b"fake image data"
        mock_doc.extract_image = MagicMock(return_value={
            "width": 500,
            "height": 500,
            "image": mock_image_data,
            "colorspace": 3,
            "bpc": 8,
        })

        with patch("pathlib.Path.exists", return_value=True):
            with patch("image_extractor.fitz.open", return_value=mock_doc):
                with patch("image_extractor.Image.frombytes") as mock_frombytes:
                    mock_pil_image = MagicMock()
                    mock_pil_image.save = MagicMock()
                    mock_frombytes.return_value = mock_pil_image

                    result = await extractor.extract(paper)

        assert result.status == PaperStatus.images_extracted
        assert len(result.images) > 0
        assert isinstance(result.images[0], ImageMetadata)
