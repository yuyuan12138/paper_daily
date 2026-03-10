"""Tests for vision configuration models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from config import Config, VisionConfig


def test_vision_config_validation():
    """Test VisionConfig can be parsed from dict."""
    data = {
        "query": {"keywords": ["test"]},
        "vision": {
            "enabled": True,
            "extraction": {
                "min_size": [300, 300],
                "max_aspect_ratio": 2.5,
                "max_images_per_paper": 15,
                "skip_duplicates": False,
            },
            "analysis": {
                "provider": "anthropic",
                "model_name": "claude-3-opus",
                "api_key_env": "ANTHROPIC_API_KEY",
                "max_tokens": 2000,
                "batch_size": 3,
                "include_context": False,
            },
            "storage": {
                "output_dir": "./custom_images",
                "format": "jpg",
            },
        },
    }
    config = Config(**data)
    assert config.vision.enabled is True
    assert config.vision.extraction.min_size == (300, 300)
    assert config.vision.extraction.max_aspect_ratio == 2.5
    assert config.vision.extraction.max_images_per_paper == 15
    assert config.vision.extraction.skip_duplicates is False
    assert config.vision.analysis.provider == "anthropic"
    assert config.vision.analysis.model_name == "claude-3-opus"
    assert config.vision.analysis.max_tokens == 2000
    assert config.vision.analysis.batch_size == 3
    assert config.vision.analysis.include_context is False
    assert config.vision.storage.output_dir == Path("./custom_images")
    assert config.vision.storage.format == "jpg"


def test_vision_disabled_by_default():
    """Test vision is disabled when not specified."""
    data = {
        "query": {"keywords": ["test"]},
    }
    config = Config(**data)
    assert config.vision.enabled is False
    assert config.vision.extraction is not None
    assert config.vision.storage is not None
