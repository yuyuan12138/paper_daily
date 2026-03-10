"""Integration tests for image pipeline integration."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from src.config import Config
from src.runner import PipelineRunner
from src.models import Paper, PaperStatus


@pytest.mark.asyncio
async def test_runner_initializes_with_vision(tmp_path):
    """Test PipelineRunner initializes with image modules when vision enabled."""
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 1

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true

model:
  provider: deepseek
  api_key_env: FAKE_API_KEY

output:
  base_dir: {tmp_path / "data"}

vision:
  enabled: true
  extraction:
    min_size: [200, 200]
    max_aspect_ratio: 3.0
    max_images_per_paper: 20
    skip_duplicates: true
  analysis:
    provider: openai
    model_name: gpt-4o
    api_key_env: OPENAI_API_KEY
    max_tokens: 1000
    batch_size: 5
  storage:
    output_dir: {tmp_path / "images"}

runtime:
  dry_run: true
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)

    # Verify config has vision enabled
    assert config.vision.enabled is True

    sample_paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    mock_fetcher = AsyncMock()
    mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])

    with patch("src.runner.ArXivFetcher", return_value=mock_fetcher):
        runner = PipelineRunner(config)

        # Verify image modules are initialized
        assert hasattr(runner, "image_extractor")
        assert hasattr(runner, "image_analyzer")
        assert runner.image_extractor is not None
        assert runner.image_analyzer is not None


@pytest.mark.asyncio
async def test_runner_skips_vision_when_disabled(tmp_path):
    """Test PipelineRunner skips image processing when vision disabled."""
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 1

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true

model:
  provider: deepseek
  api_key_env: FAKE_API_KEY

output:
  base_dir: {tmp_path / "data"}

vision:
  enabled: false

runtime:
  dry_run: true
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)

    # Verify config has vision disabled
    assert config.vision.enabled is False

    sample_paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    mock_fetcher = AsyncMock()
    mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])

    with patch("src.runner.ArXivFetcher", return_value=mock_fetcher):
        runner = PipelineRunner(config)

        # Verify image modules are NOT initialized
        assert not hasattr(runner, "image_extractor") or runner.image_extractor is None
        assert not hasattr(runner, "image_analyzer") or runner.image_analyzer is None
