# PRD Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two new sections (LLM Integration Specification and Testing & Deployment) to the existing PRD document to provide complete technical implementation details.

**Architecture:** This is a pure documentation task. The plan adds Section 18 (LLM Integration Specification) and Section 19 (Testing & Deployment) to `docs/prd.md`, then renumbers the existing Section 17 (Conclusion) to Section 20.

**Tech Stack:** Markdown documentation, no code changes required.

---

## Task 1: Add Section 18 - LLM Integration Specification

**Files:**
- Modify: `docs/prd.md` (insert after line 632, before "## 17. Conclusion")

**Step 1: Read the end of Section 16 to find insertion point**

Open `docs/prd.md` and locate the end of Section 16 (line ~632) where "## 17. Conclusion" begins.

**Step 2: Insert Section 18 header and content**

Insert the following content after Section 16 and before Section 17 (which will become Section 20):

```markdown
---

## 18. LLM Integration Specification

This section defines the technical implementation details for integrating large language models into the paper summarization pipeline.

### 18.1 Supported LLM Providers

| Provider | Models | API Library | Notes |
|----------|--------|-------------|-------|
| OpenAI | GPT-4o, GPT-4o-mini, GPT-4.1 | `openai` | Recommended for quality |
| Anthropic | Claude 3.5 Sonnet, Claude 3.5 Haiku | `anthropic` | Good for long context |
| Local | Ollama, vLLM | `ollama`, `openai-compatible` | Cost-free, slower |

### 18.2 API Integration Pattern

Abstract interface for LLM provider:

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def summarize(self, text: str, prompt: str) -> str:
        """Generate summary from text using the provider's prompt template."""
        ...

    @abstractmethod
    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count for input text."""
        ...

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for given token usage."""
        ...
```

Configuration in `config.yaml`:

```yaml
model:
  provider: openai  # openai | anthropic | local
  model_name: gpt-4o
  api_key_env: OPENAI_API_KEY
  base_url: null  # Override for local/compatible endpoints
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

**Template variables:** `{paper_title}`, `{abstract}`, `{full_text}`, `{language}`, `{summary_level}`, `{max_length}`

### 18.4 Token & Cost Estimation

| Paper Type | Avg Pages | Input Tokens | Output Tokens | Est. Cost (GPT-4o) |
|------------|-----------|--------------|---------------|-------------------|
| Short | 1-4 | 2K-4K | 500-800 | ~$0.01 |
| Medium | 5-10 | 5K-10K | 800-1.5K | ~$0.02 |
| Long | 11-20 | 15K-30K | 1.5K-3K | ~$0.05 |
| Very Long | 20+ | 40K+ | chunked | ~$0.10+ |

**Budget controls in config:**

```yaml
model:
  max_cost_per_batch: 5.0  # USD
  warn_cost_threshold: 2.0
  max_input_tokens: 100000
```

### 18.5 Chunking Strategy for Long Papers

When input exceeds model context window:

1. **Semantic chunking**: Split by section (Introduction, Method, Experiments, Conclusion)
2. **Two-pass summarization**:
   - Pass 1: Summarize each chunk independently
   - Pass 2: Aggregate chunk summaries into final output
3. **Fallback**: If still too long, provide brief summary of each section

### 18.6 Rate Limiting & Retry

```yaml
runtime:
  # Rate limiting (requests per minute)
  rate_limit_rpm: 60
  rate_limit_tpm: 200000  # tokens per minute

  # Retry configuration
  retry_times: 3
  retry_backoff: exponential  # exponential | linear
  retry_base_delay: 1.0  # seconds
```

**Error handling:**
- `429 Too Many Requests`: Exponential backoff, retry
- `500+ Server Errors`: Retry up to 3 times
- `400 Invalid Request`: Log and skip (don't retry)
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
```

**Step 3: Verify Section 18 was inserted correctly**

Check that:
- Section 18 appears between Section 16 and Section 17
- All markdown formatting is correct
- Code blocks are properly formatted

**Step 4: Commit**

```bash
git add docs/prd.md
git commit -m "docs: add Section 18 - LLM Integration Specification"
```

---

## Task 2: Add Section 19 - Testing & Deployment

**Files:**
- Modify: `docs/prd.md` (insert after Section 18, before "## 17. Conclusion")

**Step 1: Insert Section 19 header and content**

Insert the following content after Section 18:

```markdown
## 19. Testing & Deployment

This section defines the testing strategy and deployment considerations for the AutoPaper Pipeline.

### 19.1 Testing Strategy

#### 19.1.1 Unit Testing

Each module should have dedicated unit tests with mocked dependencies:

```
tests/
├── unit/
│   ├── test_fetcher.py       # Test arXiv API calls (mocked)
│   ├── test_downloader.py    # Test PDF download logic
│   ├── test_parser.py        # Test PDF text extraction
│   ├── test_summarizer.py    # Test LLM integration (mocked)
│   ├── test_renderer.py      # Test Markdown generation
│   └── test_state_manager.py # Test state persistence
├── integration/
│   ├── test_pipeline.py      # End-to-end with mocks
│   └── test_config.py        # Config loading/validation
└── fixtures/
    ├── sample_arxiv_response.json
    ├── sample_paper.pdf
    └── sample_parsed_text.txt
```

**Coverage target:** ≥80% for core modules

**Key test scenarios:**
- ArXiv API returns empty results
- PDF download fails (404, timeout)
- PDF is password-protected or scanned
- LLM API returns invalid JSON
- State file is corrupted
- Disk full scenarios

#### 19.1.2 Integration Testing

Use pytest with mock responses for external APIs:

```python
# Example: Test with mocked arXiv response
import pytest
from tests.fixtures import load_fixture

@pytest.fixture
def mock_arxiv_response():
    return load_fixture("sample_arxiv_response.json")

@pytest.mark.asyncio
async def test_paper_retrieval(mock_arxiv_response):
    fetcher = ArXivFetcher()
    papers = await fetcher.fetch(keywords=["LLM"])
    assert len(papers) > 0
    assert papers[0].arxiv_id is not None
```

#### 19.1.3 End-to-End Testing

Create a "dry run" mode that processes 1-2 test papers without real LLM calls:

```bash
# Run E2E test with mocks
python main.py --config test_config.yaml --dry-run --max-papers 1
```

Use pre-cached responses for LLM to test the full pipeline deterministically.

### 19.2 Configuration Validation

Add config schema validation using `pydantic` or `jsonschema`:

```python
from pydantic import BaseModel, Field, validator
import re

class QueryConfig(BaseModel):
    keywords: list[str] = Field(min_items=1)
    categories: list[str] = []
    max_results: int = Field(gt=0, le=100)

    @validator("categories")
    def validate_arxiv_categories(cls, v):
        for cat in v:
            if not re.match(r"^[A-Z]{2}\.[A-Z]{2}$", cat):
                raise ValueError(f"Invalid arXiv category: {cat}")
        return v
```

### 19.3 CI/CD Pipeline

#### 19.3.1 GitHub Actions Example

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv pip install -e ".[dev]"
      - name: Run linter
        run: ruff check .
      - name: Run type checker
        run: mypy src/
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      - name: Validate config schema
        run: python -c "from src.config import validate_config; validate_config('config/config.yaml')"
```

### 19.4 Deployment Options

#### 19.4.1 Local CLI Installation

```bash
# Using uv
uv pip install -e .
paper-daily --config config.yaml
```

#### 19.4.2 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv pip install -e .
ENTRYPOINT ["python", "main.py"]
```

```yaml
# docker-compose.yml
services:
  paper-daily:
    build: .
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

#### 19.4.3 Scheduled Execution (cron)

```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/paper_daily && uv run python main.py --config config.yaml >> logs/cron.log 2>&1
```

Or use `systemd` timer for better logging and recovery.

### 19.5 Monitoring & Observability

#### 19.5.1 Logging

```yaml
logging:
  level: INFO  # DEBUG | INFO | WARNING | ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    - type: file
      path: logs/pipeline.log
      max_size: 10MB
      backup_count: 5
    - type: console
```

#### 19.5.2 Metrics to Track

Create a simple metrics file after each run:

```json
// data/metrics/2026-03-10.json
{
  "run_id": "20260310-090000",
  "papers_processed": 15,
  "papers_succeeded": 13,
  "papers_failed": 2,
  "total_cost_usd": 0.35,
  "duration_seconds": 320,
  "errors": {
    "download_failed": 1,
    "parse_failed": 0,
    "summarize_failed": 1
  }
}
```

#### 19.5.3 Health Checks

For containerized deployments, add a health check endpoint:

```bash
# Simple health check
python main.py --health-check
# Returns: OK | ERROR: <reason>
```

### 19.6 Dependency Management

```toml
# pyproject.toml
[project]
name = "paper-daily"
version = "0.1.0"
dependencies = [
    "arxiv>=2.0.0",
    "PyPDF2>=3.0.0",
    "openai>=1.0.0",
    "anthropic>=0.40.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.8.0",
    "mypy>=1.8.0",
]
```

### 19.7 Error Recovery

```yaml
runtime:
  # Continue on individual paper failures
  continue_on_error: true

  # Save checkpoint after every N papers
  checkpoint_interval: 5

  # Resume from last checkpoint on restart
  resume_from_checkpoint: true
```

---
```

**Step 2: Verify Section 19 was inserted correctly**

Check that:
- Section 19 appears after Section 18 and before Section 17
- All markdown formatting is correct
- Code blocks and YAML examples are properly formatted

**Step 3: Commit**

```bash
git add docs/prd.md
git commit -m "docs: add Section 19 - Testing & Deployment"
```

---

## Task 3: Renumber Section 17 to Section 20

**Files:**
- Modify: `docs/prd.md` (line ~634, change "## 17. Conclusion" to "## 20. Conclusion")

**Step 1: Update Conclusion section number**

Find the line containing "## 17. Conclusion" and change it to:

```markdown
## 20. Conclusion
```

**Step 2: Verify the change**

Confirm that:
- The section header now reads "## 20. Conclusion"
- No other section numbers were affected
- The document structure is complete with sections 1-20

**Step 3: Commit**

```bash
git add docs/prd.md
git commit -m "docs: renumber Conclusion section from 17 to 20"
```

---

## Task 4: Final Validation

**Files:**
- Verify: `docs/prd.md`

**Step 1: Validate document structure**

Run the following checks:

```bash
# Check all section headers are present
grep "^## " docs/prd.md | sort
```

Expected output should show sections 1-20 in order:
- 1. Document Information
- 2. Product Background
- ...
- 16. Technical Implementation Suggestions
- 18. LLM Integration Specification
- 19. Testing & Deployment
- 20. Conclusion

**Step 2: Verify markdown syntax**

Check for any markdown formatting errors:

```bash
# If you have a markdown linter installed
# markdownlint docs/prd.md
```

**Step 3: Manual review**

Open `docs/prd.md` and verify:
1. Section 18 (LLM Integration Specification) is complete
2. Section 19 (Testing & Deployment) is complete
3. Section 20 (Conclusion) is properly renumbered
4. All code blocks are properly formatted with triple backticks
5. All tables are properly formatted
6. No duplicate or broken section headers

**Step 4: Final commit**

```bash
git add docs/prd.md
git commit -m "docs: complete PRD optimization with sections 18-19"
```

---

## Summary

After completing all tasks:
1. Section 18 (LLM Integration Specification) added with provider support, API patterns, prompt templates, token/cost estimation, chunking, rate limiting, and observability details
2. Section 19 (Testing & Deployment) added with testing strategy, CI/CD pipeline, deployment options, monitoring, and dependency management
3. Section 17 renumbered to Section 20 (Conclusion)
4. Document validated for correct structure and formatting

The PRD now provides complete technical implementation details for both LLM integration and testing/deployment considerations.
