# PRD: One-Click Automated Paper Retrieval, Analysis, and Summarization System

## 1. Document Information

**Product Name**: AutoPaper Pipeline
**Document Type**: PRD (Product Requirements Document)
**Version**: v1.0
**Author**: To be filled
**Date**: 2026-03-10

---

## 2. Product Background

Researchers, graduate students, and technical professionals need to continuously track newly published papers on arXiv and quickly determine whether they are worth reading in depth. The current mainstream workflow usually involves manually searching keywords, opening paper pages one by one, downloading PDFs, reading abstracts and methods, and then manually organizing notes. This workflow has the following problems:

1. **Inefficient information acquisition**: A significant amount of time is spent filtering papers every day.
2. **High information organization cost**: After reading, users still need to manually summarize the core contributions, methods, experiments, and limitations.
3. **Obvious repetitive work**: For fixed research directions, users often repeat the same search process every day.
4. **Lack of unified knowledge accumulation**: Paper summaries are scattered across local files, note-taking tools, and chat records, making them difficult to track and reuse.

Therefore, an automated workflow that supports **one-click execution** is needed: automatically retrieve target papers from arXiv, complete text extraction, structural analysis, and content summarization, and output standardized Markdown documents to help users quickly complete paper screening and knowledge accumulation.

---

## 3. Product Goals

### 3.1 Core Goals

Build a one-click automated paper processing workflow that can:

1. Automatically retrieve papers from arXiv based on user-configured topics, keywords, or categories.
2. Automatically download paper metadata and PDFs.
3. Automatically parse paper content.
4. Automatically generate structured summaries.
5. Automatically output Markdown documents for archiving, retrieval, and further editing.

### 3.2 Product Value

* Automate the workflow of “finding papers → downloading → reading → summarizing → archiving.”
* Reduce the cost of tracking papers and improve literature review efficiency.
* Build a standardized, searchable, and reusable paper knowledge base.
* Provide foundational capabilities for future extensions such as vector retrieval, topic clustering, daily/weekly reports, and knowledge graphs.

### 3.3 Success Criteria

After launch, the system should meet the following minimum standards:

1. Users only need to execute one command to complete the entire workflow from paper retrieval to Markdown output.
2. For a given topic, the system can reliably retrieve papers and successfully generate summary documents.
3. The output for each paper includes key fields such as title, authors, abstract, core method, innovations, experimental conclusions, limitations, and keywords.
4. The output is readable and supports quick decisions on whether the paper deserves a deeper reading.

---

## 4. User Profiles

### 4.1 Target Users

1. **Master’s / PhD students**: Need to continuously track the latest papers in a research direction.
2. **Academic researchers**: Need to quickly conduct literature reviews and topic exploration.
3. **AI engineers / algorithm engineers**: Need to track progress in models, methods, and applications.
4. **Technical team leads**: Hope to obtain domain updates automatically and accumulate knowledge in a structured way.

### 4.2 User Pain Points

* They do not want to manually search for papers every day.
* They do not have time to read every paper in full and only want to review structured summaries quickly.
* They need Markdown-formatted outputs that can be directly saved, edited, and shared.
* They want the system to be “as automated as possible,” rather than requiring manual confirmation at every step.

---

## 5. Use Cases

### Scenario 1: Daily tracking of new papers

The user configures keywords such as “large language model, reinforcement learning, multimodal,” runs one command every day, and the system automatically retrieves the latest papers and generates corresponding Markdown summaries.

### Scenario 2: Topic-specific literature research

The user performs a focused search on “DNA methylation site prediction,” and the system batch-retrieves relevant papers and generates summary documents for literature review writing.

### Scenario 3: Team knowledge accumulation

A team maintains a shared paper analysis repository. After each run, the system automatically saves summaries of new papers to a specified directory for all team members to browse and reuse.

---

## 6. Product Scope

### 6.1 In Scope

This version focuses on the following capabilities:

1. Retrieve paper metadata from arXiv.
2. Support retrieval by keywords, categories, and time range.
3. Automatically download paper PDFs.
4. Automatically extract paper text content.
5. Generate structured summaries based on large language models.
6. Output Markdown documents for single papers or in batches.
7. Support one-click execution.
8. Support basic logging, retry on failure, and deduplication.

### 6.2 Out of Scope

1. No web-based UI.
2. No aggregation of multiple data sources such as Semantic Scholar, PubMed, or OpenReview.
3. No high-precision chart understanding or formula-level reasoning.
4. No automatic generation of full survey paper content.
5. No complex collaboration permission management.

---

## 7. Core Functional Requirements

## 7.1 One-Click Entry Point

### Feature Description

Users launch the entire workflow with a single command, without step-by-step manual operations.

### Inputs

* Configuration file (such as YAML / JSON) or command-line arguments
* Search keywords
* arXiv categories
* Time range
* Output directory
* Maximum number of papers to retrieve

### Outputs

* Execution logs
* Downloaded PDF files
* Structured Markdown summary files

### Requirement Details

1. Support one-click execution from the command line, for example:
   `python main.py --config config.yaml`
2. Support defining retrieval and output rules through configuration files.
3. Support a dry-run mode that only shows which papers would be retrieved, without downloading or summarizing them.

---

## 7.2 arXiv Paper Retrieval Module

### Feature Description

Based on the configuration, the system automatically calls the arXiv data source to retrieve a list of papers that match the conditions.

### Requirement Details

1. Support keyword-based retrieval.

2. Support arXiv category-based retrieval.

3. Support sorting by time or filtering by submission date.

4. Support setting the maximum number of retrieved papers.

5. Support retrieving the following metadata:

   * Title
   * Authors
   * Abstract
   * arXiv ID
   * Submission date
   * Categories
   * PDF link
   * Paper homepage link

6. Support deduplication to avoid repeatedly processing already retrieved papers.

### Acceptance Criteria

* Given keywords, the system can return a list of matching papers.
* The retrieval result includes the required metadata.
* Repeated runs do not re-download the same paper.

---

## 7.3 PDF Download Module

### Feature Description

Based on paper metadata, the system automatically downloads PDFs to a local directory.

### Requirement Details

1. Support automatic downloading from arXiv PDF links.
2. Support retry on download failure.
3. Support standardized file naming, for example: `arxiv_id_title.pdf`.
4. Support skipping files that already exist locally.
5. Support recording download status.

### Acceptance Criteria

* Valid paper links can be successfully downloaded as PDFs.
* The system can automatically retry when network fluctuations occur.
* Existing local files with the same name are skipped by default.

---

## 7.4 Text Parsing Module

### Feature Description

The system extracts text content from PDFs for downstream summarization.

### Requirement Details

1. Support PDF text extraction.

2. Support basic cleaning, including removing extra blank lines, headers, footers, and garbled fragments.

3. Support coarse-grained section-based splitting.

4. Prioritize preserving the following content:

   * Title
   * Abstract
   * Introduction
   * Methods
   * Experiments
   * Conclusion

5. If PDF parsing fails, the system should record the reason and skip that paper.

### Acceptance Criteria

* Most text-based PDFs can be parsed into usable body text.
* The parsed result can be directly used by the downstream summarization module.

---

## 7.5 Paper Analysis and Summarization Module

### Feature Description

The system uses a large language model to understand and summarize paper content, producing structured results.

### Requirement Details

1. Support generating summaries in a unified format.

2. Summary fields should include at least:

   * Basic information
   * Research problem
   * Core method
   * Innovations
   * Experimental setup
   * Main results
   * Limitations
   * Applicable scenarios
   * Keywords
   * Whether it is worth reading in depth (optional)

3. Support output language control (Chinese / English).

4. Support summary length control (brief / standard / detailed).

5. Support prompt template configuration for future adjustment.

6. Support segmenting exceptionally long texts before aggregation.

### Acceptance Criteria

* Output fields are complete and structurally consistent.
* Document format remains consistent across different papers.
* Users can directly read the Markdown output to understand the core content of a paper.

---

## 7.6 Markdown Generation Module

### Feature Description

The system integrates paper metadata and model-generated summaries into Markdown documents.

### Requirement Details

1. Generate one independent Markdown file for each paper.

2. Support unified template-based output.

3. Recommended Markdown content includes:

   * Title
   * Paper metadata
   * Original abstract
   * Auto-generated summary
   * Key conclusions
   * Follow-up reading recommendations

4. Support batch generation of index files such as `README.md` or `index.md`.

5. Support safe filename processing to avoid illegal characters.

### Example Markdown Structure

```md
# Paper Title

## Metadata
- arXiv ID:
- Authors:
- Submitted Date:
- Categories:
- PDF:
- URL:

## Abstract
...

## Summary
### Research Problem
...

### Core Method
...

### Contributions
...

### Experiments
...

### Limitations
...

### Keywords
- ...
- ...

## Recommendation
...
```

### Acceptance Criteria

* Generated Markdown files can be directly opened and read locally.
* The template is consistent and all required fields are included.

---

## 7.7 Task Tracking and Deduplication Module

### Feature Description

The system records papers that have already been processed to avoid repeated downloading and repeated summarization.

### Requirement Details

1. Use arXiv ID as the primary key for tracking processing status.

2. Status values should include at least:

   * discovered
   * downloaded
   * parsed
   * summarized
   * failed

3. Support incremental execution.

4. Support reprocessing failed papers later.

### Acceptance Criteria

* Completed papers are not reprocessed during the second run.
* Users can determine the failure stage based on the status.

---

## 7.8 Logging and Error Handling

### Feature Description

The system provides complete logs to help locate workflow issues.

### Requirement Details

1. Record logs for key workflow stages.
2. Record the processing status of each paper.
3. Separately record reasons for download failure, parsing failure, and model invocation failure.
4. Support basic retry strategies.
5. Failure on a single paper should not affect the overall batch process.

### Acceptance Criteria

* Users can quickly identify the failed step when errors occur.
* The overall workflow is recoverable.

---

## 8. Non-Functional Requirements

### 8.1 Usability

1. Provide a clear configuration file structure.
2. Users should be able to run the system without understanding internal implementation details.
3. The output directory structure should be clear.

### 8.2 Stability

1. Network requests should support retries.
2. Failure on a single paper should not affect the overall task.
3. Repeated runs should produce consistent and reproducible results.

### 8.3 Scalability

1. It should be extendable to other paper sources in the future.
2. It should support integration with different large language models in the future.
3. It should support future capabilities such as daily reports, email notifications, and vector retrieval.

### 8.4 Performance

1. Support batch processing of multiple papers.
2. Long-text summarization should support chunk-based processing.
3. End-to-end execution should be completed within reasonable resource constraints.

### 8.5 Maintainability

1. Modules should be clearly separated.
2. Configuration should be decoupled from code.
3. Prompt templates should be maintained independently.

---

## 9. Typical Workflow

### 9.1 End-to-End Main Workflow

1. The user executes the one-click command.
2. The system reads the configuration.
3. The system retrieves the paper list from arXiv.
4. The system filters out already processed papers.
5. The system downloads the target PDFs.
6. The system extracts and cleans the text.
7. The system calls a large language model to generate structured summaries.
8. The system outputs Markdown files.
9. The system updates processing status and logs.

### 9.2 Exception Workflow

* Download failure: mark as `failed` after retries still fail.
* PDF parsing failure: mark as `failed` and save the error reason.
* Model invocation failure: retry, and mark as failed if it still does not succeed.
* Output file write failure: terminate processing for the current paper and record the error.

---

## 10. Recommended Output Directory Structure

```text
project/
├─ config/
│  └─ config.yaml
├─ data/
│  ├─ metadata/
│  ├─ pdfs/
│  ├─ parsed/
│  └─ summaries/
├─ logs/
│  └─ pipeline.log
├─ prompts/
│  └─ summary_prompt.md
├─ state/
│  └─ paper_state.json
└─ main.py
```

---

## 11. Recommended Configuration

```yaml
query:
  keywords:
    - large language model
    - reinforcement learning
  categories:
    - cs.CL
    - cs.AI
  max_results: 20
  sort_by: submittedDate
  sort_order: descending

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true
  language: zh
  summary_level: standard

output:
  base_dir: ./data
  overwrite: false

model:
  provider: openai
  model_name: gpt-4.1
  temperature: 0.2

runtime:
  retry_times: 3
  timeout_sec: 60
  dry_run: false
```

---

## 12. MVP Definition

### MVP Goal

Deliver a runnable version in the shortest possible cycle to validate the availability of the workflow: “automatic retrieval + automatic summarization + Markdown output.”

### MVP Includes

1. Support keyword-based arXiv retrieval.
2. Support PDF downloading.
3. Support text extraction.
4. Support calling a single large language model for summarization.
5. Support Markdown output.
6. Support basic deduplication and logging.

### MVP Excludes

1. Multi-model switching.
2. Chart recognition.
3. Advanced ranking and scoring.
4. Visual interface.
5. Automatic scheduled execution.

---

## 13. Future Iteration Directions

### Phase 2

1. Add scheduled task capability for daily automatic execution.
2. Add support for multiple data sources.
3. Add topic clustering and deduplication-based recommendation.
4. Add a per-paper scoring mechanism, such as novelty, relevance, and reproducibility.

### Phase 3

1. Build a paper knowledge base and retrieval system.
2. Support question-answering-based retrieval.
3. Support comparative analysis across multiple papers.
4. Support automatic generation of weekly reports, survey drafts, and research roadmaps.

---

## 14. Risks and Mitigation

### Risk 1: Unstable PDF parsing quality

**Description**: Some double-column papers, scanned PDFs, and formula-dense pages may affect parsing quality.
**Mitigation**: Prioritize text-based PDFs; preserve the original abstract; record and skip papers when parsing fails.

### Risk 2: Model summaries may hallucinate

**Description**: Large language models may misread paper content or add information that does not exist.
**Mitigation**: Clearly distinguish between the “original abstract” and the “model-generated summary” in the output; generate summaries based on extracted text as much as possible; citation-backed evidence can be added later.

### Risk 3: Long texts exceed the model context window

**Description**: A full paper may exceed the model’s input limit.
**Mitigation**: Use a segmented summarization plus aggregated summarization strategy.

### Risk 4: Repeated processing and inconsistent state

**Description**: Interrupted batch tasks may result in partial files and inconsistent state.
**Mitigation**: Introduce a state file and record progress step by step.

### Risk 5: High noise in arXiv search results

**Description**: Keyword-based retrieval may introduce irrelevant papers.
**Mitigation**: Add category filtering, keyword enhancement, and a downstream relevance scoring module.

---

## 15. Key Metrics

### 15.1 Functional Metrics

1. Paper retrieval success rate
2. PDF download success rate
3. Text parsing success rate
4. Markdown generation success rate

### 15.2 Quality Metrics

1. Summary field completeness rate
2. Summary readability
3. Subjective user satisfaction
4. In-depth reading recommendation hit rate (optional)

### 15.3 Efficiency Metrics

1. Average processing time per paper
2. Total processing time for batch tasks
3. Time saved by repeated runs

---

## 16. Technical Implementation Suggestions (for Engineering Reference)

### Recommended Module Breakdown

1. `fetcher`: arXiv retrieval and metadata acquisition
2. `downloader`: PDF downloading
3. `parser`: PDF text extraction and cleaning
4. `summarizer`: large language model summarization
5. `renderer`: Markdown generation
6. `state_manager`: state management and deduplication
7. `runner`: main workflow orchestration

### Recommended Execution Method

* One-click CLI execution
* Configuration-driven
* Log persistence
* Independent modules for easier unit testing

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
| Rate limit hit | Wait and retry with backoff |
| Cost threshold exceeded | Stop batch and warn user |

---

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

## 20. Conclusion

This product is designed to address the low efficiency of paper tracking and preliminary reading. Through a one-click automated workflow, it creates a complete closed loop from retrieving papers from arXiv, downloading PDFs, analyzing content, and generating Markdown summaries. During the MVP phase, the focus is on validating the usability and stability of the end-to-end workflow, and the product can later be gradually expanded into a research knowledge management platform.
