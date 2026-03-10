"""Tests for LLM summarizer module."""

from datetime import datetime
from unittest.mock import patch, AsyncMock
import pytest
from config import ModelConfig
from models import Paper, PaperStatus
from summarizer import PaperSummarizer


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    """Set fake API key for all tests."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-api-key")


@pytest.mark.asyncio
async def test_summarize_success():
    """Test successful paper summarization."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(model_config=model_config)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="This is the full paper text content...",
    )

    with patch.object(summarizer, "_call_llm", return_value='{"research_problem": "Test problem", "core_method": "Test method"}'):
        result = await summarizer.summarize(paper)

    assert result.summary is not None
    assert result.summary["research_problem"] == "Test problem"
    assert result.status == PaperStatus.summarized


@pytest.mark.asyncio
async def test_summarize_with_language_setting():
    """Test summarization with language setting."""
    model_config = ModelConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    summarizer = PaperSummarizer(model_config=model_config, language="zh", summary_level="detailed")

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="Full text...",
    )

    mock_response = AsyncMock()
    mock_response.choices = [type("Choice", (), {
        "message": type("Message", (), {"content": '{"research_problem": "测试问题"}'})()
    })()]

    with patch("summarizer.AsyncOpenAI"):
        with patch.object(summarizer, "_create_prompt", return_value="prompt"):
            with patch.object(summarizer, "_call_llm", return_value='{"research_problem": "测试问题"}'):
                result = await summarizer.summarize(paper)

    assert result.summary is not None


@pytest.mark.asyncio
async def test_summarize_missing_text():
    """Test summarization when parsed text is missing."""
    summarizer = PaperSummarizer(model_config=ModelConfig())

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        # parsed_text is None
    )

    result = await summarizer.summarize(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_summarize_llm_error():
    """Test handling LLM API error."""
    summarizer = PaperSummarizer(model_config=ModelConfig())

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="Full text...",
    )

    with patch("summarizer.AsyncOpenAI") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        result = await summarizer.summarize(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_summarize_invalid_json_response():
    """Test handling invalid JSON response from LLM."""
    summarizer = PaperSummarizer(model_config=ModelConfig())

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        parsed_text="Full text...",
    )

    mock_response = AsyncMock()
    mock_response.choices = [type("Choice", (), {
        "message": type("Message", (), {"content": "Not valid JSON"})()
    })()]

    with patch("summarizer.AsyncOpenAI") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await summarizer.summarize(paper)

    assert result.status == PaperStatus.failed
