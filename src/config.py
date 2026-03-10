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


class VisionExtractionConfig(BaseModel):
    """Configuration for image extraction from PDFs."""

    min_size: tuple[int, int] = (200, 200)
    max_aspect_ratio: float = 3.0
    max_images_per_paper: int = Field(gt=0, le=50, default=20)
    skip_duplicates: bool = True


class VisionAnalysisConfig(BaseModel):
    """Configuration for image analysis using LLMs."""

    provider: str = Field(pattern="^(openai|anthropic)$", default="openai")
    model_name: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    max_tokens: int = Field(gt=0, le=4000, default=1000)
    batch_size: int = Field(gt=0, le=10, default=5)
    include_context: bool = True


class VisionStorageConfig(BaseModel):
    """Configuration for storing extracted images."""

    output_dir: Path = Path("./data/images")
    format: str = "png"


class VisionConfig(BaseModel):
    """Configuration for vision (image extraction and analysis)."""

    enabled: bool = False
    extraction: VisionExtractionConfig = Field(default_factory=VisionExtractionConfig)
    analysis: VisionAnalysisConfig | None = None
    storage: VisionStorageConfig = Field(default_factory=VisionStorageConfig)


class Config(BaseModel):
    """Main configuration container."""

    query: QueryConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(path)
        with path.open() as f:
            data = yaml.safe_load(f)
        return cls(**data)
