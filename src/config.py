"""Configuration loading and validation using Pydantic."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class QueryConfig(BaseModel):
    """Configuration for querying arXiv."""

    keywords: list[str] = Field(min_length=1)
    categories: list[str] = Field(default_factory=list)
    max_results: int = Field(gt=0, le=100, default=10)
    sort_by: str = "submittedDate"
    sort_order: Literal["ascending", "descending"] = "descending"


class PipelineConfig(BaseModel):
    """Configuration for pipeline stages."""

    download_pdf: bool = True
    parse_pdf: bool = True
    summarize: bool = True
    output_markdown: bool = True
    language: Literal["en", "zh"] = "zh"
    summary_level: Literal["brief", "standard", "detailed"] = "standard"


class ModelConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: str = "deepseek"
    base_url: str | None = None
    model_name: str = "deepseek-chat"
    api_key_env: str = "DEEPSEEK_API_KEY"
    temperature: float = Field(ge=0, le=2, default=0.2)
    max_tokens: int = Field(gt=0, default=4000)


class OutputConfig(BaseModel):
    """Configuration for output directories."""

    base_dir: Path = Field(default=Path("./data"))
    overwrite: bool = False


class RuntimeConfig(BaseModel):
    """Configuration for runtime behavior."""

    retry_times: int = Field(ge=0, default=3)
    timeout_sec: int = Field(gt=0, default=60)
    dry_run: bool = False
    continue_on_error: bool = True


class Config(BaseModel):
    """Main configuration container."""

    query: QueryConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(path)
        with path.open() as f:
            data = yaml.safe_load(f)
        return cls(**data)
