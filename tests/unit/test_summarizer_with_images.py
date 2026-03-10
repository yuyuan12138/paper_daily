"""Tests for summarizer with image context."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

from config import ModelConfig
from models import Paper, PaperStatus, ImageMetadata, ImageAnalysis
from summarizer import PaperSummarizer


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    """Set fake API key for all tests."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-api-key")


@pytest.mark.asyncio
async def test_summarizer_creates_prompt_with_images():
    """Test image context is included in prompt."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(
        model_config=model_config,
        prompts_dir=Path("prompts"),
    )

    # Create paper with analyzed images
    image1 = ImageMetadata(
        path=Path("figure1.png"),
        page_number=1,
        figure_number="1",
        caption="Architecture diagram",
        analysis=ImageAnalysis(
            description="Shows the proposed architecture with three main components",
            key_findings=["Encoder-decoder structure", "Attention mechanism", "Three-stage pipeline"],
            relevance="high",
        ),
    )

    image2 = ImageMetadata(
        path=Path("figure2.png"),
        page_number=3,
        figure_number="2",
        caption="Experimental results",
        analysis=ImageAnalysis(
            description="Bar chart comparing accuracy across datasets",
            key_findings=["15% improvement over baseline", "Best on Dataset A"],
            relevance="high",
        ),
    )

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper with Images",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="This is the full paper text content...",
        images=[image1, image2],
    )

    # Create prompt
    prompt = summarizer._create_prompt(paper)

    # Verify image context is included in prompt
    assert "Figure 1" in prompt
    assert "Page 1" in prompt
    assert "Shows the proposed architecture" in prompt
    assert "Encoder-decoder structure" in prompt

    assert "Figure 2" in prompt
    assert "Page 3" in prompt
    assert "Bar chart comparing accuracy" in prompt
    assert "15% improvement over baseline" in prompt

    # Verify figures analysis section exists
    assert "Figures Analysis" in prompt


@pytest.mark.asyncio
async def test_summarizer_no_images():
    """Test prompt when paper has no images."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(
        model_config=model_config,
        prompts_dir=Path("prompts"),
    )

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="This is the full paper text content...",
        images=[],
    )

    # Create prompt
    prompt = summarizer._create_prompt(paper)

    # Verify paper info is still included
    assert "Test Paper" in prompt
    assert "Test abstract" in prompt


@pytest.mark.asyncio
async def test_summarizer_images_without_analysis():
    """Test prompt when images don't have analysis."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(
        model_config=model_config,
        prompts_dir=Path("prompts"),
    )

    # Image without analysis
    image = ImageMetadata(
        path=Path("figure1.png"),
        page_number=1,
        analysis=None,  # No analysis
    )

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="This is the full paper text content...",
        images=[image],
    )

    # Create prompt
    prompt = summarizer._create_prompt(paper)

    # Verify no figures analysis section is added when no images have analysis
    assert "Figures Analysis" not in prompt or prompt.count("Figure") == 0


@pytest.mark.asyncio
async def test_create_prompt_with_images_context():
    """Test _create_prompt_with_images_context method directly."""
    model_config = ModelConfig(provider="deepseek", model_name="deepseek-chat")
    summarizer = PaperSummarizer(model_config=model_config)

    # Test with empty list
    result = summarizer._create_prompt_with_images_context([])
    assert result == ""

    # Test with images with analysis
    images = [
        ImageMetadata(
            path=Path("fig1.png"),
            page_number=1,
            analysis=ImageAnalysis(
                description="Test description",
                key_findings=["Finding 1", "Finding 2"],
                relevance="high",
            ),
        ),
    ]

    result = summarizer._create_prompt_with_images_context(images)

    assert "Figure 1" in result
    assert "Page 1" in result
    assert "Test description" in result
    assert "Finding 1" in result
    assert "Finding 2" in result
    assert "high" in result


@pytest.mark.asyncio
async def test_summarize_with_images_integration():
    """Test end-to-end summarization with images."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(
        model_config=model_config,
        prompts_dir=Path("prompts"),
    )

    image = ImageMetadata(
        path=Path("figure1.png"),
        page_number=1,
        analysis=ImageAnalysis(
            description="Proposed method architecture",
            key_findings=["Novel algorithm", "Efficient computation"],
            relevance="high",
        ),
    )

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="Full paper text...",
        images=[image],
    )

    with patch.object(summarizer, "_call_llm", return_value='{"research_problem": "Test", "core_method": "Test"}'):
        result = await summarizer.summarize(paper)

    assert result.status == PaperStatus.summarized
    assert result.summary is not None
