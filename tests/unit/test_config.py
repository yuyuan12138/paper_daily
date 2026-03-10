"""Unit tests for configuration module."""

from pathlib import Path
from pydantic import ValidationError
import pytest
from src.config import Config, QueryConfig, PipelineConfig, ModelConfig, OutputConfig, RuntimeConfig


def test_query_config_validation():
    """Test QueryConfig validation."""
    config = QueryConfig(
        keywords=["machine learning"],
        categories=["cs.AI"],
        max_results=20,
    )
    assert config.keywords == ["machine learning"]
    assert config.categories == ["cs.AI"]
    assert config.max_results == 20
    assert config.sort_by == "submittedDate"  # default
    assert config.sort_order == "descending"  # default


def test_query_config_max_results_validation():
    """Test that max_results must be positive and <= 100."""
    with pytest.raises(ValidationError):
        QueryConfig(keywords=["test"], max_results=0)

    with pytest.raises(ValidationError):
        QueryConfig(keywords=["test"], max_results=101)


def test_query_config_requires_keywords():
    """Test that keywords cannot be empty."""
    with pytest.raises(ValidationError):
        QueryConfig(keywords=[])


def test_model_config_deepseek():
    """Test ModelConfig with Deepseek provider."""
    config = ModelConfig(
        provider="deepseek",
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    )
    assert config.provider == "deepseek"
    assert config.base_url == "https://api.deepseek.com/v1"
    assert config.model_name == "deepseek-chat"
    assert config.api_key_env == "DEEPSEEK_API_KEY"
    assert config.temperature == 0.2  # default
    assert config.max_tokens == 4000  # default


def test_runtime_config_defaults():
    """Test RuntimeConfig default values."""
    config = RuntimeConfig()
    assert config.retry_times == 3
    assert config.timeout_sec == 60
    assert config.dry_run is False
    assert config.continue_on_error is True


def test_pipeline_config_defaults():
    """Test PipelineConfig default values."""
    config = PipelineConfig()
    assert config.download_pdf is True
    assert config.parse_pdf is True
    assert config.summarize is True
    assert config.output_markdown is True
    assert config.language == "zh"
    assert config.summary_level == "standard"


def test_load_config_from_yaml(tmp_path):
    """Test loading config from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
query:
  keywords: ["test"]
  max_results: 5

pipeline:
  download_pdf: true
  summarize: true
  language: zh

model:
  provider: deepseek
  model_name: deepseek-chat
  api_key_env: DEEPSEEK_API_KEY

output:
  base_dir: ./data

runtime:
  dry_run: false
""")

    config = Config.from_yaml(config_file)
    assert config.query.keywords == ["test"]
    assert config.query.max_results == 5
    assert config.pipeline.summarize is True
    assert config.pipeline.language == "zh"
