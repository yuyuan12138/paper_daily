# PRD Optimization Design

**Date**: 2026-03-10
**Author**: Claude
**Status**: Approved

## Overview

This document defines the optimization of the AutoPaper Pipeline PRD by adding two new sections focused on LLM integration technical details and testing/deployment strategies.

## Changes to PRD

The PRD (`docs/prd.md`) will be extended with two new sections:

1. **Section 18: LLM Integration Specification**
2. **Section 19: Testing & Deployment**

These sections will be added after the existing Section 17 (Conclusion), which will be renumbered to Section 20.

---

## Section 18: LLM Integration Specification

### 18.1 Supported LLM Providers

| Provider | Models | API Library | Notes |
|----------|--------|-------------|-------|
| OpenAI | GPT-4o, GPT-4o-mini, GPT-4.1 | `openai` | Recommended for quality |
| Anthropic | Claude 3.5 Sonnet, Claude 3.5 Haiku | `anthropic` | Good for long context |
| Local | Ollama, vLLM | `ollama`, `openai-compatible` | Cost-free, slower |

### 18.2 API Integration Pattern

Abstract interface for LLM provider:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def summarize(self, text: str, prompt: str) -> str: ...

    @abstractmethod
    async def estimate_tokens(self, text: str) -> int: ...

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float: ...
```

Configuration in `config.yaml`:

```yaml
model:
  provider: openai  # openai | anthropic | local
  model_name: gpt-4o
  api_key_env: OPENAI_API_KEY
  base_url: null
  temperature: 0.2
  max_tokens: 4000
```

### 18.3 Prompt Template Architecture

Prompt templates stored in `prompts/` directory:

```
prompts/
├── summary_template.md      # Main summarization prompt
├── summary_zh.md           # Chinese output variant
├── summary_brief.md        # Brief version
├── summary_detailed.md     # Detailed version
└── chunk_aggregation.md    # For combining long-paper summaries
```

Template variables: `{paper_title}`, `{abstract}`, `{full_text}`, `{language}`, `{summary_level}`, `{max_length}`

### 18.4 Token & Cost Estimation

| Paper Type | Avg Pages | Input Tokens | Output Tokens | Est. Cost (GPT-4o) |
|------------|-----------|--------------|---------------|-------------------|
| Short | 1-4 | 2K-4K | 500-800 | ~$0.01 |
| Medium | 5-10 | 5K-10K | 800-1.5K | ~$0.02 |
| Long | 11-20 | 15K-30K | 1.5K-3K | ~$0.05 |
| Very Long | 20+ | 40K+ | chunked | ~$0.10+ |

Budget controls in config:

```yaml
model:
  max_cost_per_batch: 5.0
  warn_cost_threshold: 2.0
  max_input_tokens: 100000
```

### 18.5 Chunking Strategy for Long Papers

When input exceeds model context window:

1. **Semantic chunking**: Split by section (Introduction, Method, Experiments, Conclusion)
2. **Two-pass summarization**: Summarize each chunk, then aggregate
3. **Fallback**: Brief summary of each section if still too long

### 18.6 Rate Limiting & Retry

```yaml
runtime:
  rate_limit_rpm: 60
  rate_limit_tpm: 200000
  retry_times: 3
  retry_backoff: exponential
  retry_base_delay: 1.0
```

Error handling:
- `429 Too Many Requests`: Exponential backoff, retry
- `500+ Server Errors`: Retry up to 3 times
- `400 Invalid Request`: Log and skip
- Network errors: Retry with exponential backoff

### 18.7 Fallback Strategies

| Scenario | Fallback Action |
|----------|-----------------|
| Primary API unreachable | Try secondary provider if configured |
| Context length exceeded | Enable chunking mode |
- Per-model cost tracking
- Rate limit hit counts
- Average tokens per paper

---

## Section 19: Testing & Deployment

### 19.1 Testing Strategy

#### 19.1.1 Unit Testing

```
tests/
├── unit/
│   ├── test_fetcher.py
│   ├── test_downloader.py
│   ├── test_parser.py
│   ├── test_summarizer.py
│   ├── test_renderer.py
│   └── test_state_manager.py
├── integration/
│   ├── test_pipeline.py
│   └── test_config.py
└── fixtures/
    ├── sample_arxiv_response.json
    ├── sample_paper.pdf
    └── sample_parsed_text.txt
```

Coverage target: ≥80%

#### 19.1.2 Integration Testing

Use pytest with mock responses for external APIs.

#### 19.1.3 End-to-End Testing

```bash
python main.py --config test_config.yaml --dry-run --max-papers 1
```

### 19.2 Configuration Validation

Add schema validation using `pydantic`:

```python
from pydantic import BaseModel, Field, validator

class QueryConfig(BaseModel):
    keywords: list[str] = Field(min_items=1)
    categories: list[str] = []
    max_results: int = Field(gt=0, le=100)
```

### 19.3 CI/CD Pipeline

GitHub Actions example with linting, type checking, and tests.

### 19.4 Deployment Options

- Local CLI installation with uv
- Docker deployment with docker-compose
- Scheduled execution via cron or systemd

### 19.5 Monitoring & Observability

#### Logging

```yaml
logging:
  level: INFO
  handlers:
    - type: file
      path: logs/pipeline.log
    - type: console
```

#### Metrics

```json
{
  "run_id": "20260310-090000",
  "papers_processed": 15,
  "papers_succeeded": 13,
  "total_cost_usd": 0.35,
  "duration_seconds": 320
}
```

### 19.6 Dependency Management

Use `pyproject.toml` with uv for dependency management.

### 19.7 Error Recovery

```yaml
runtime:
  continue_on_error: true
  checkpoint_interval: 5
  resume_from_checkpoint: true
```

---

## Implementation Notes

1. The existing Section 17 (Conclusion) will be renumbered to Section 20
2. All subsequent section references will need updating
3. The document structure will maintain consistency with existing formatting
4. Code examples use Python 3.13 syntax
