# AutoPaper Pipeline MVP Design

**Date**: 2026-03-10
**Author**: Claude
**Status**: Approved

## Overview

Design for the full MVP implementation of the AutoPaper Pipeline system - a one-click automated paper retrieval, analysis, and summarization system.

### Scope Decisions

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| Build Scope | Full MVP (all 6 core modules) | Validate complete workflow end-to-end |
| LLM Provider | Deepseek (OpenAI-compatible) | Cost-effective, strong performance |
| Project Structure | PRD-recommended modular | Clear separation of concerns |
| Testing | Full TDD (80%+ coverage) | Higher code quality, maintainable |

---

## Architecture Overview

### Pipeline Architecture

Papers flow through discrete stages with state tracking:

```
arXiv API → Fetcher → Downloader → Parser → Summarizer → Renderer → Markdown Files
                ↓            ↓         ↓          ↓
            State Manager tracks progress at each stage
```

**Key characteristics**:
- Each module is independently testable
- Clear interfaces between modules
- Async I/O for network operations
- State persistence for resumability

### Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| Package Manager | uv |
| Config | YAML + Pydantic |
| HTTP Client | httpx (async) |
| PDF Parsing | pypdf |
| LLM Client | openai (Deepseek compatible) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |
| Type Checking | mypy |

---

## Module Breakdown

### Core Data Model

```python
@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    submitted_date: datetime
    categories: list[str]
    pdf_url: str
    pdf_path: Path | None = None
    parsed_text: str | None = None
    summary: dict | None = None
    status: PaperStatus = PaperStatus.discovered

enum PaperStatus:
    discovered = "discovered"     # Retrieved from arXiv
    downloaded = "downloaded"     # PDF saved locally
    parsed = "parsed"             # Text extracted
    summarized = "summarized"     # LLM summary complete
    failed = "failed"             # Error at any stage
```

### Module Specifications

| Module | File | Responsibility | Input | Output |
|--------|------|---------------|-------|--------|
| `config` | `src/config.py` | Load/validate YAML config | Path to config.yaml | Config object |
| `state_manager` | `src/state_manager.py` | Track paper processing status | Paper + status | Persisted JSON |
| `fetcher` | `src/fetcher.py` | Query arXiv API | Keywords, categories | list[Paper] |
| `downloader` | `src/downloader.py` | Download PDFs | Paper with pdf_url | Paper with pdf_path |
| `parser` | `src/parser.py` | Extract text from PDF | Paper with pdf_path | Paper with parsed_text |
| `summarizer` | `src/summarizer.py` | LLM summarization | Paper with parsed_text | Paper with summary |
| `renderer` | `src/renderer.py` | Generate Markdown | Complete Paper | .md file |
| `runner` | `src/runner.py` | Orchestrate pipeline | Config | Complete run |

---

## Directory Structure

```
paper_daily/
├── config/
│   └── config.yaml              # Default configuration
├── data/
│   ├── metadata/                # Paper metadata cache
│   ├── pdfs/                    # Downloaded PDFs
│   ├── parsed/                  # Extracted text (optional)
│   ├── summaries/               # Generated Markdown files
│   └── metrics/                 # Run metrics
├── logs/
│   └── pipeline.log
├── prompts/
│   ├── summary_template.md      # Main summarization prompt
│   ├── summary_zh.md            # Chinese output variant
│   ├── summary_brief.md         # Brief version
│   └── summary_detailed.md      # Detailed version
├── state/
│   └── paper_state.json         # Processing state
├── src/
│   ├── __init__.py
│   ├── config.py                # Config loading & validation
│   ├── models.py                # Paper dataclass and enums
│   ├── state_manager.py         # State persistence
│   ├── fetcher.py               # arXiv API client
│   ├── downloader.py            # PDF download
│   ├── parser.py                # PDF text extraction
│   ├── summarizer.py            # LLM integration
│   ├── renderer.py              # Markdown generation
│   └── runner.py                # Pipeline orchestration
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_state_manager.py
│   │   ├── test_fetcher.py
│   │   ├── test_downloader.py
│   │   ├── test_parser.py
│   │   ├── test_summarizer.py
│   │   └── test_renderer.py
│   ├── integration/
│   │   └── test_pipeline.py
│   ├── fixtures/
│   │   ├── sample_arxiv_response.json
│   │   ├── sample_paper.pdf
│   │   └── sample_summary.json
│   └── conftest.py
├── main.py                      # CLI entry point
├── pyproject.toml
└── README.md
```

---

## Configuration

### pyproject.toml

```toml
[project]
name = "paper-daily"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "arxiv>=2.0.0",
    "httpx>=0.27.0",
    "pypdf>=3.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0",
    "openai>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.8.0",
    "mypy>=1.8.0",
]

[project.scripts]
paper-daily = "main:main"
```

### config.yaml

```yaml
query:
  keywords: ["large language model"]
  categories: []
  max_results: 10
  sort_by: submittedDate
  sort_order: descending

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true
  language: zh
  summary_level: standard

model:
  provider: deepseek
  base_url: "https://api.deepseek.com/v1"
  model_name: "deepseek-chat"
  api_key_env: DEEPSEEK_API_KEY
  temperature: 0.2
  max_tokens: 4000

output:
  base_dir: ./data
  overwrite: false

runtime:
  retry_times: 3
  timeout_sec: 60
  dry_run: false
  continue_on_error: true
```

---

## Error Handling

### Error Handling Strategy

| Error Type | Handling Approach |
|------------|------------------|
| Network failures (arXiv, PDF) | Exponential backoff retry (3x) |
| PDF parse failure | Mark as `failed`, log reason, continue |
| LLM API rate limit | Wait with backoff, retry |
| LLM API auth failure | Fail fast, don't retry |
| Disk I/O failure | Fail fast, alert user |
| Single paper failure | Log and continue (if `continue_on_error: true`) |

### State File Format

`state/paper_state.json`:

```json
{
  "last_run": "2026-03-10T12:00:00Z",
  "papers": {
    "2401.12345": {
      "status": "summarized",
      "pdf_path": "./data/pdfs/2401.12345.pdf",
      "markdown_path": "./data/summaries/2401.12345.md",
      "updated_at": "2026-03-10T12:05:00Z",
      "error": null
    }
  }
}
```

---

## Testing Strategy (TDD)

### Test Structure

```
tests/
├── unit/                     # Unit tests per module
├── integration/              # End-to-end with mocks
├── fixtures/                 # Test data
└── conftest.py              # Shared pytest fixtures
```

### TDD Workflow per Module

1. **Red**: Write failing test for desired behavior
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Clean up implementation
4. **Repeat** until module complete

### Key Fixtures

```python
@pytest.fixture
def mock_arxiv_response():
    """Cached arXiv API response for testing"""

@pytest.fixture
def sample_paper():
    """Sample Paper object for testing"""

@pytest.fixture
def mock_llm_response():
    """Mock LLM summary response"""
```

### Coverage Target

- Unit tests: ≥80% coverage for core modules
- Integration tests: End-to-end pipeline validation
- All tests use mocks for external APIs (arXiv, LLM)

---

## Implementation Sequence

Modules should be implemented in dependency order:

1. **config** - Foundation, no dependencies
2. **models** - Data structures
3. **state_manager** - State persistence
4. **fetcher** - arXiv API client
5. **downloader** - PDF download
6. **parser** - PDF text extraction
7. **summarizer** - LLM integration
8. **renderer** - Markdown generation
9. **runner** - Pipeline orchestration
10. **main.py** - CLI entry point

Each module follows TDD: write tests first, then implement.

---

## CLI Interface

```bash
# Basic usage
paper-daily --config config.yaml

# Dry run (no actual downloads/summarization)
paper-daily --config config.yaml --dry-run

# Limit number of papers
paper-daily --config config.yaml --max-papers 5

# Reprocess failed papers
paper-daily --config config.yaml --retry-failed
```

---

## Success Criteria

The MVP is complete when:

1. ✅ Single command retrieves papers from arXiv
2. ✅ PDFs are downloaded to `data/pdfs/`
3. ✅ Text is extracted from PDFs
4. ✅ LLM generates structured summaries
5. ✅ Markdown files are written to `data/summaries/`
6. ✅ State is persisted for deduplication
7. ✅ Errors are logged and don't crash the pipeline
8. ✅ Unit tests achieve ≥80% coverage
9. ✅ Integration tests validate end-to-end flow

---

## Next Steps

This design will be used to create a detailed implementation plan using the writing-plans skill.
