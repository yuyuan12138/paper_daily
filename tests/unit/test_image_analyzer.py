"""Unit tests for ImageAnalyzer module."""

import base64
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI

from models import Paper, PaperStatus, ImageMetadata, ImageAnalysis
from src.image_analyzer import ImageAnalyzer


class TestImageAnalyzerInitialization:
    """Tests for ImageAnalyzer initialization."""

    def test_analyzer_initialization(self):
        """Test ImageAnalyzer can be initialized with default parameters."""
        analyzer = ImageAnalyzer()
        assert analyzer.provider == "openai"
        assert analyzer.model_name == "gpt-4o"
        assert analyzer.api_key_env == "OPENAI_API_KEY"
        assert analyzer.base_url is None
        assert analyzer.max_tokens == 1000
        assert analyzer.batch_size == 5

    def test_analyzer_initialization_custom_params(self):
        """Test ImageAnalyzer can be initialized with custom parameters."""
        analyzer = ImageAnalyzer(
            provider="anthropic",
            model_name="claude-3-opus-20240229",
            api_key_env="ANTHROPIC_API_KEY",
            base_url="https://api.anthropic.com",
            max_tokens=2000,
            batch_size=10,
        )
        assert analyzer.provider == "anthropic"
        assert analyzer.model_name == "claude-3-opus-20240229"
        assert analyzer.api_key_env == "ANTHROPIC_API_KEY"
        assert analyzer.base_url == "https://api.anthropic.com"
        assert analyzer.max_tokens == 2000
        assert analyzer.batch_size == 10


class TestImageAnalyzerAnalyze:
    """Tests for ImageAnalyzer.analyze method."""

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return Paper(
            arxiv_id="2401.12345",
            title="Test Paper Title",
            authors=["Author One", "Author Two"],
            abstract="Test abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            images=[],
        )

    @pytest.mark.asyncio
    async def test_analyze_empty_images(self, sample_paper):
        """Test handles paper with no images."""
        analyzer = ImageAnalyzer()

        result = await analyzer.analyze(sample_paper)

        assert result.status == PaperStatus.images_analyzed
        assert result.images == []

    @pytest.mark.asyncio
    async def test_analyze_paper_without_images_attribute(self):
        """Test paper without images attribute initializes empty list."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        )
        analyzer = ImageAnalyzer()

        result = await analyzer.analyze(paper)

        assert result.status == PaperStatus.images_analyzed
        assert result.images == []


class TestCreateAnalysisPrompt:
    """Tests for ImageAnalyzer._create_analysis_prompt method."""

    def test_create_analysis_prompt_with_title(self):
        """Test prompt includes paper title."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="A Novel Approach to Deep Learning",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        )
        img = ImageMetadata(path=Path("figure_1_0.png"), page_number=1)

        analyzer = ImageAnalyzer()
        prompt = analyzer._create_analysis_prompt(paper, img)

        assert "A Novel Approach to Deep Learning" in prompt

    def test_create_analysis_prompt_with_caption(self):
        """Test prompt includes image caption when available."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        )
        img = ImageMetadata(
            path=Path("figure_1_0.png"),
            page_number=1,
            caption="Training loss curves over 100 epochs",
        )

        analyzer = ImageAnalyzer()
        prompt = analyzer._create_analysis_prompt(paper, img)

        assert "Training loss curves over 100 epochs" in prompt

    def test_create_analysis_prompt_requests_json(self):
        """Test prompt requests JSON response."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        )
        img = ImageMetadata(path=Path("figure_1_0.png"), page_number=1)

        analyzer = ImageAnalyzer()
        prompt = analyzer._create_analysis_prompt(paper, img)

        assert "image_type" in prompt
        assert "description" in prompt
        assert "key_findings" in prompt
        assert "relevance" in prompt


class TestParseAnalysisResponse:
    """Tests for ImageAnalyzer._parse_analysis_response method."""

    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response."""
        analyzer = ImageAnalyzer()
        content = """{
            "description": "A bar chart showing results",
            "key_findings": ["Result A is higher", "Result B is lower"],
            "relevance": "high"
        }"""

        result = analyzer._parse_analysis_response(content)

        assert result.description == "A bar chart showing results"
        assert result.key_findings == ["Result A is higher", "Result B is lower"]
        assert result.relevance == "high"

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        analyzer = ImageAnalyzer()
        content = """```json
{
    "description": "Neural network architecture",
    "key_findings": ["Three layers", "Uses ReLU activation"],
    "relevance": "medium"
}
```"""

        result = analyzer._parse_analysis_response(content)

        assert result.description == "Neural network architecture"
        assert result.key_findings == ["Three layers", "Uses ReLU activation"]
        assert result.relevance == "medium"

    def test_parse_invalid_json_returns_default(self):
        """Test invalid JSON returns default analysis."""
        analyzer = ImageAnalyzer()
        content = "This is not valid JSON"

        result = analyzer._parse_analysis_response(content)

        assert result.description == "Failed to analyze image"
        assert result.key_findings == []
        assert result.relevance == "low"


class TestReadImageAsBase64:
    """Tests for ImageAnalyzer._read_image_as_base64 method."""

    @pytest.fixture
    def temp_image_file(self, tmp_path):
        """Create a temporary image file for testing."""
        # Create a simple 1x1 PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        image_path = tmp_path / "test_image.png"
        image_path.write_bytes(png_data)
        return image_path, png_data

    def test_read_image_as_base64(self, temp_image_file):
        """Test reading image file as base64."""
        image_path, expected_data = temp_image_file
        analyzer = ImageAnalyzer()
        result = analyzer._read_image_as_base64(image_path)

        # Should be valid base64 and decode to original data
        decoded = base64.b64decode(result)
        assert decoded == expected_data


class TestAnalyzeWithMockedAPI:
    """Tests for image analysis with mocked API calls."""

    @pytest.mark.asyncio
    async def test_analyze_batch_with_openai(self):
        """Test batch analysis with OpenAI provider."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            images=[
                ImageMetadata(path=Path("figure_1_0.png"), page_number=1),
                ImageMetadata(path=Path("figure_1_1.png"), page_number=1),
            ],
        )

        analyzer = ImageAnalyzer(provider="openai", batch_size=2)

        # Mock the _analyze_single_image method to return a successful analysis
        mock_analysis = ImageAnalysis(
            description="Test description",
            key_findings=["test finding"],
            relevance="high",
        )
        with patch.object(
            analyzer, "_analyze_single_image", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = mock_analysis
            await analyzer.analyze(paper)

        assert paper.status == PaperStatus.images_analyzed
        assert len(paper.images) == 2
        assert paper.images[0].analysis is not None

    @pytest.mark.asyncio
    async def test_analyze_graceful_degradation_on_error(self):
        """Test graceful degradation when analysis fails."""
        paper = Paper(
            arxiv_id="2401.12345",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            submitted_date=datetime(2024, 1, 1),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            images=[ImageMetadata(path=Path("figure_1_0.png"), page_number=1)],
        )

        analyzer = ImageAnalyzer()

        # Mock to raise an error
        with patch.object(
            analyzer, "_analyze_single_image", side_effect=Exception("API error")
        ):
            result = await analyzer.analyze(paper)

        # Should fall back to images_extracted status
        assert result.status == PaperStatus.images_extracted
