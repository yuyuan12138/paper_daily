# AutoPaper Pipeline MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a one-click automated paper retrieval, analysis, and summarization system that fetches papers from arXiv, downloads PDFs, extracts text, generates LLM summaries, and outputs Markdown documents.

**Architecture:** Pipeline architecture where papers flow through discrete stages (fetch → download → parse → summarize → render) with state tracking for resumability. Each module is independently testable with clear interfaces.

**Tech Stack:** Python 3.13, uv for package management, Pydantic for config, httpx for async HTTP, pypdf for PDF parsing, OpenAI SDK (Deepseek-compatible), pytest for TDD.

---

## Task 1: Project Setup and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`

**Step 1: Create pyproject.toml**

Create `pyproject.toml` with project metadata and dependencies:

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

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create src directory with __init__.py**

Create: `src/__init__.py`

```python
"""Paper Daily - Automated paper retrieval and summarization."""
__version__ = "0.1.0"
```

**Step 3: Install dependencies**

Run: `uv pip install -e .`

**Step 4: Create base directories**

Run: `mkdir -p config data/{metadata,pdfs,parsed,summaries,metrics} logs prompts state tests/{unit,integration,fixtures}`

**Step 5: Commit**

```bash
git add pyproject.toml src/__init__.py
git commit -m "feat: project setup with pyproject.toml and base structure"
```

---

## Task 2: Core Data Models

**Files:**
- Create: `src/models.py`
- Test: `tests/unit/test_models.py`

**Step 1: Write failing test for Paper dataclass**

Create `tests/unit/test_models.py`:

```python
from datetime import datetime
from pathlib import Path
from src.models import Paper, PaperStatus


def test_paper_creation():
    """Test creating a Paper object with required fields."""
    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One", "Author Two"],
        abstract="This is a test abstract.",
        submitted_date=datetime(2024, 1, 1, 12, 0, 0),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )
    assert paper.arxiv_id == "2401.12345"
    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.status == PaperStatus.discovered
    assert paper.pdf_path is None
    assert paper.parsed_text is None
    assert paper.summary is None


def test_paper_status_enum():
    """Test PaperStatus enum values."""
    assert PaperStatus.discovered.value == "discovered"
    assert PaperStatus.downloaded.value == "downloaded"
    assert PaperStatus.parsed.value == "parsed"
    assert PaperStatus.summarized.value == "summarized"
    assert PaperStatus.failed.value == "failed"


def test_paper_with_optional_fields():
    """Test Paper object with optional fields populated."""
    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author One"],
        abstract="Test abstract",
        submitted_date=datetime(2024, 1, 1),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
        parsed_text="Extracted text content",
        summary={"research_problem": "Test problem"},
        status=PaperStatus.summarized,
    )
    assert paper.pdf_path == Path("/data/pdfs/2401.12345.pdf")
    assert paper.parsed_text == "Extracted text content"
    assert paper.summary == {"research_problem": "Test problem"}
    assert paper.status == PaperStatus.summarized
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models.py -v`
Expected: FAIL with "cannot import name 'Paper' from 'src.models'"

**Step 3: Implement models.py**

Create `src/models.py`:

```python
"""Core data models for the paper pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class PaperStatus(Enum):
    """Processing status of a paper in the pipeline."""

    discovered = "discovered"  # Retrieved from arXiv
    downloaded = "downloaded"  # PDF saved locally
    parsed = "parsed"  # Text extracted
    summarized = "summarized"  # LLM summary complete
    failed = "failed"  # Error at any stage


@dataclass
class Paper:
    """Represents a research paper from arXiv."""

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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/unit/test_models.py src/models.py
git commit -m "feat: add Paper dataclass and PaperStatus enum"
```

---

## Task 3: Configuration Module

**Files:**
- Create: `src/config.py`
- Create: `config/config.yaml`
- Test: `tests/unit/test_config.py`

**Step 1: Write failing test for config loading**

Create `tests/unit/test_config.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL with import errors

**Step 3: Implement config.py**

Create `src/config.py`:

```python
"""Configuration loading and validation using Pydantic."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS (7 tests)

**Step 5: Create default config.yaml**

Create `config/config.yaml`:

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

**Step 6: Commit**

```bash
git add src/config.py tests/unit/test_config.py config/config.yaml
git commit -m "feat: add configuration module with Pydantic validation"
```

---

## Task 4: State Manager Module

**Files:**
- Create: `src/state_manager.py`
- Test: `tests/unit/test_state_manager.py`

**Step 1: Write failing test for state manager**

Create `tests/unit/test_state_manager.py`:

```python
from datetime import datetime
from pathlib import Path
import pytest
import json
from src.models import Paper, PaperStatus
from src.state_manager import StateManager


def test_state_manager_init(tmp_path):
    """Test StateManager initialization."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    assert manager.state_file == state_file
    assert manager.state == {"last_run": None, "papers": {}}


def test_get_paper_status_not_found():
    """Test getting status for non-existent paper."""
    manager = StateManager(Path("/tmp/test_state.json"))
    status = manager.get_paper_status("2401.99999")
    assert status is None


def test_update_paper_status():
    """Test updating paper status."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status(
        arxiv_id="2401.12345",
        status=PaperStatus.downloaded,
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
    )
    paper_state = manager.get_paper_status("2401.12345")
    assert paper_state["status"] == "downloaded"
    assert paper_state["pdf_path"] == "/data/pdfs/2401.12345.pdf"
    assert paper_state["error"] is None


def test_update_paper_with_error():
    """Test updating paper status with error."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status(
        arxiv_id="2401.12345",
        status=PaperStatus.failed,
        error="Download failed: 404",
    )
    paper_state = manager.get_paper_status("2401.12345")
    assert paper_state["status"] == "failed"
    assert paper_state["error"] == "Download failed: 404"


def test_is_paper_processed():
    """Test checking if paper is already processed."""
    manager = StateManager(Path("/tmp/test_state.json"))
    assert manager.is_paper_processed("2401.12345") is False

    manager.update_paper_status("2401.12345", PaperStatus.summarized)
    assert manager.is_paper_processed("2401.12345") is True


def test_save_and_load_state(tmp_path):
    """Test saving and loading state from file."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)

    manager.update_last_run()
    manager.update_paper_status("2401.12345", PaperStatus.downloaded)
    manager.save()

    # Load state in new manager
    manager2 = StateManager(state_file)
    manager2.load()
    assert manager2.state["last_run"] is not None
    assert manager2.get_paper_status("2401.12345")["status"] == "downloaded"


def test_get_papers_by_status():
    """Test getting papers filtered by status."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status("2401.11111", PaperStatus.downloaded)
    manager.update_paper_status("2401.22222", PaperStatus.failed)
    manager.update_paper_status("2401.33333", PaperStatus.summarized)

    failed = manager.get_papers_by_status(PaperStatus.failed)
    assert failed == ["2401.22222"]

    downloaded = manager.get_papers_by_status(PaperStatus.downloaded)
    assert set(downloaded) == {"2401.11111"}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_state_manager.py -v`
Expected: FAIL with import errors

**Step 3: Implement state_manager.py**

Create `src/state_manager.py`:

```python
"""State management for paper processing tracking."""

from datetime import datetime
from pathlib import Path
import json
from src.models import PaperStatus


class StateManager:
    """Manages persistent state for paper processing."""

    def __init__(self, state_file: Path | str):
        """Initialize state manager with state file path."""
        self.state_file = Path(state_file)
        self.state = {"last_run": None, "papers": {}}

    def load(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            with self.state_file.open() as f:
                self.state = json.load(f)

    def save(self) -> None:
        """Save state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_paper_status(self, arxiv_id: str) -> dict | None:
        """Get status entry for a paper."""
        return self.state["papers"].get(arxiv_id)

    def update_paper_status(
        self,
        arxiv_id: str,
        status: PaperStatus,
        pdf_path: Path | None = None,
        markdown_path: Path | None = None,
        error: str | None = None,
    ) -> None:
        """Update processing status for a paper."""
        if arxiv_id not in self.state["papers"]:
            self.state["papers"][arxiv_id] = {}

        entry = self.state["papers"][arxiv_id]
        entry["status"] = status.value
        entry["updated_at"] = datetime.now().isoformat()

        if pdf_path:
            entry["pdf_path"] = str(pdf_path)
        if markdown_path:
            entry["markdown_path"] = str(markdown_path)
        if error:
            entry["error"] = error
        elif "error" in entry:
            del entry["error"]

    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if paper has been fully processed."""
        entry = self.get_paper_status(arxiv_id)
        if not entry:
            return False
        return entry["status"] == PaperStatus.summarized.value

    def get_papers_by_status(self, status: PaperStatus) -> list[str]:
        """Get all paper IDs with a given status."""
        return [
            arxiv_id
            for arxiv_id, entry in self.state["papers"].items()
            if entry["status"] == status.value
        ]

    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.state["last_run"] = datetime.now().isoformat()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_state_manager.py -v`
Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add src/state_manager.py tests/unit/test_state_manager.py
git commit -m "feat: add state manager for tracking paper processing"
```

---

## Task 5: ArXiv Fetcher Module

**Files:**
- Create: `src/fetcher.py`
- Test: `tests/unit/test_fetcher.py`
- Fixture: `tests/fixtures/sample_arxiv_response.json`

**Step 1: Create arXiv response fixture**

Create `tests/fixtures/sample_arxiv_response.json`:

```json
{
  "entries": [
    {
      "id": "http://arxiv.org/abs/2401.12345",
      "title": "Attention Is All You Need",
      "summary": "We propose a new simple network architecture, the Transformer...",
      "published": "2024-01-01T12:00:00Z",
      "categories": ["cs.AI", "cs.LG"],
      "authors": [
        {"name": "Vaswani, Ashish"},
        {"name": "Shazeer, Noam"}
      ],
      "links": [
        {
          "href": "http://arxiv.org/pdf/2401.12345v1.pdf",
          "title": "pdf",
          "type": "application/pdf"
        }
      ]
    }
  ]
}
```

**Step 2: Write failing test for fetcher**

Create `tests/unit/test_fetcher.py`:

```python
from datetime import datetime
from unittest.mock import AsyncMock, patch
import pytest
from src.config import QueryConfig
from src.fetcher import ArXivFetcher
from src.models import Paper


@pytest.mark.asyncio
async def test_fetch_papers_by_keywords():
    """Test fetching papers by keywords."""
    query_config = QueryConfig(
        keywords=["transformer", "attention"],
        max_results=10,
    )
    fetcher = ArXivFetcher(query_config)

    # Mock arxiv.Client
    with patch("src.fetcher.arxiv.Client") as mock_client:
        mock_results = [
            type("Result", (), {
                "entry_id": "http://arxiv.org/abs/2401.12345",
                "title": "Test Paper",
                "summary": "Test abstract",
                "published": datetime(2024, 1, 1, 12, 0, 0),
                "categories": ["cs.AI"],
                "authors": [type("Author", (), {"name": "Test Author"})()],
                "pdf_url": "http://arxiv.org/pdf/2401.12345.pdf",
            })()
        ]
        mock_client.return_value.__enter__.return_value.results.return_value = mock_results

        papers = await fetcher.fetch()

    assert len(papers) == 1
    assert papers[0].arxiv_id == "2401.12345"
    assert papers[0].title == "Test Paper"
    assert papers[0].authors == ["Test Author"]
    assert papers[0].status == "discovered"


@pytest.mark.asyncio
async def test_fetch_with_categories():
    """Test fetching papers with category filter."""
    query_config = QueryConfig(
        keywords=["machine learning"],
        categories=["cs.AI", "cs.LG"],
        max_results=5,
    )
    fetcher = ArXivFetcher(query_config)

    with patch("src.fetcher.arxiv.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.results.return_value = []

        papers = await fetcher.fetch()

    assert isinstance(papers, list)


@pytest.mark.asyncio
async def test_fetch_empty_results():
    """Test handling empty search results."""
    query_config = QueryConfig(keywords=["nonexistent"], max_results=10)
    fetcher = ArXivFetcher(query_config)

    with patch("src.fetcher.arxiv.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.results.return_value = []

        papers = await fetcher.fetch()

    assert papers == []


@pytest.mark.asyncio
async def test_extract_arxiv_id():
    """Test extracting arXiv ID from various URL formats."""
    fetcher = ArXivFetcher(QueryConfig(keywords=["test"]))

    assert fetcher._extract_arxiv_id("http://arxiv.org/abs/2401.12345v1") == "2401.12345"
    assert fetcher._extract_arxiv_id("http://arxiv.org/abs/2401.12345") == "2401.12345"
    assert fetcher._extract_arxiv_id("2401.12345v1") == "2401.12345"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_fetcher.py -v`
Expected: FAIL with import errors

**Step 4: Implement fetcher.py**

Create `src/fetcher.py`:

```python
"""ArXiv paper fetcher using the arxiv library."""

import re
from datetime import datetime
from typing import Self

import arxiv

from src.config import QueryConfig
from src.models import Paper, PaperStatus


class ArXivFetcher:
    """Fetches paper metadata from arXiv."""

    def __init__(self, config: QueryConfig) -> None:
        """Initialize fetcher with query configuration."""
        self.config = config

    async def fetch(self) -> list[Paper]:
        """Fetch papers from arXiv based on configuration."""
        # Build query string
        query_parts = []
        for keyword in self.config.keywords:
            query_parts.append(f'all:"{keyword}"')
        for category in self.config.categories:
            query_parts.append(f"cat:{category}")

        query_str = " OR ".join(query_parts) if query_parts else "all:*"

        # Create search
        search = arxiv.Search(
            query=query_str,
            max_results=self.config.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=(
                arxiv.SortOrder.Descending
                if self.config.sort_order == "descending"
                else arxiv.SortOrder.Ascending
            ),
        )

        papers = []
        with arxiv.Client() as client:
            for result in client.results(search):
                paper = Paper(
                    arxiv_id=self._extract_arxiv_id(result.entry_id),
                    title=result.title,
                    authors=[a.name for a in result.authors],
                    abstract=result.summary.replace("\n", " ").strip(),
                    submitted_date=result.published,
                    categories=result.categories,
                    pdf_url=result.pdf_url,
                    status=PaperStatus.discovered,
                )
                papers.append(paper)

        return papers

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """Extract arXiv ID from entry ID or URL."""
        # Match patterns like "2401.12345v1" or "2401.12345"
        match = re.search(r"(\d{4}\.\d+)", entry_id)
        if match:
            return match.group(1)
        # Fallback: return as-is if pattern doesn't match
        return entry_id.split("v")[0] if "v" in entry_id else entry_id
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_fetcher.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add src/fetcher.py tests/unit/test_fetcher.py tests/fixtures/sample_arxiv_response.json
git commit -m "feat: add arXiv fetcher module"
```

---

## Task 6: PDF Downloader Module

**Files:**
- Create: `src/downloader.py`
- Test: `tests/unit/test_downloader.py`

**Step 1: Write failing test for downloader**

Create `tests/unit/test_downloader.py`:

```python
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import HTTPStatusError, TimeoutException
from src.models import Paper, PaperStatus
from src.downloader import PDFDownloader


@pytest.mark.asyncio
async def test_download_pdf_success(tmp_path):
    """Test successful PDF download."""
    downloader = PDFDownloader(base_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    # Mock httpx async stream
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.aread.return_value = b"fake pdf content"

        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = mock_stream

        result = await downloader.download(paper)

    assert result.pdf_path is not None
    assert result.pdf_path.name == "2401.12345.pdf"
    assert result.status == PaperStatus.downloaded
    assert result.pdf_path.exists()


@pytest.mark.asyncio
async def test_download_skip_if_exists(tmp_path):
    """Test skipping download if PDF already exists."""
    downloader = PDFDownloader(base_dir=tmp_dir=tmp_path)

    # Create existing PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    existing_pdf = pdf_dir / "2401.12345.pdf"
    existing_pdf.write_bytes(b"existing content")

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    result = await downloader.download(paper)

    assert result.pdf_path == existing_pdf
    assert result.status == PaperStatus.downloaded
    # Content should not change
    assert result.pdf_path.read_bytes() == b"existing content"


@pytest.mark.asyncio
async def test_download_with_retry_on_timeout():
    """Test retry behavior on timeout."""
    downloader = PDFDownloader(retry_times=2, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        # First call times out, second succeeds
        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.aread.return_value = b"pdf content"

        mock_client.return_value.__aenter__.return_value.stream.side_effect = [
            TimeoutException("Timeout"),
            mock_stream,
        ]

        result = await downloader.download(paper)

    assert result.status == PaperStatus.downloaded


@pytest.mark.asyncio
async def test_download_failure_after_retries():
    """Test marking as failed after max retries."""
    downloader = PDFDownloader(retry_times=1, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream.side_effect = TimeoutException("Timeout")

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_download_404_not_found():
    """Test handling 404 error without retry."""
    downloader = PDFDownloader(retry_times=3, base_dir=Path("/tmp"))

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
    )

    with patch("src.downloader.httpx.AsyncClient") as mock_client:
        response = MagicMock()
        response.status_code = 404

        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = response
        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.raise_for_status.side_effect = HTTPStatusError(
            "Not found", request=MagicMock(), response=response
        )

        result = await downloader.download(paper)

    assert result.status == PaperStatus.failed
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_downloader.py -v`
Expected: FAIL with import errors

**Step 3: Implement downloader.py**

Create `src/downloader.py`:

```python
"""PDF downloader module with retry logic."""

import asyncio
from pathlib import Path
from typing import Self

import httpx
from httpx import HTTPStatusError, TimeoutException

from src.models import Paper, PaperStatus


class PDFDownloader:
    """Downloads PDF files from arXiv."""

    def __init__(
        self,
        base_dir: Path,
        retry_times: int = 3,
        timeout_sec: int = 60,
    ) -> None:
        """Initialize downloader with configuration."""
        self.base_dir = base_dir
        self.retry_times = retry_times
        self.timeout_sec = timeout_sec
        self.pdf_dir = base_dir / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, paper: Paper) -> Paper:
        """Download PDF for a paper."""
        pdf_path = self.pdf_dir / f"{paper.arxiv_id}.pdf"

        # Skip if already exists
        if pdf_path.exists():
            paper.pdf_path = pdf_path
            paper.status = PaperStatus.downloaded
            return paper

        # Download with retry
        for attempt in range(self.retry_times + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    async with client.stream("GET", paper.pdf_url) as response:
                        response.raise_for_status()
                        content = await response.aread()
                        pdf_path.write_bytes(content)

                paper.pdf_path = pdf_path
                paper.status = PaperStatus.downloaded
                return paper

            except TimeoutException:
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    paper.status = PaperStatus.failed
                    return paper

            except HTTPStatusError as e:
                if e.response.status_code in (404, 403):
                    # Don't retry client errors
                    paper.status = PaperStatus.failed
                    return paper
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)
                else:
                    paper.status = PaperStatus.failed
                    return paper

            except Exception:
                if attempt < self.retry_times:
                    await asyncio.sleep(2**attempt)
                else:
                    paper.status = PaperStatus.failed
                    return paper

        paper.status = PaperStatus.failed
        return paper
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_downloader.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/downloader.py tests/unit/test_downloader.py
git commit -m "feat: add PDF downloader with retry logic"
```

---

## Task 7: PDF Parser Module

**Files:**
- Create: `src/parser.py`
- Test: `tests/unit/test_parser.py`

**Step 1: Write failing test for parser**

Create `tests/unit/test_parser.py`:

```python
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
from src.models import Paper, PaperStatus
from src.parser import PDFParser


@pytest.mark.asyncio
async def test_parse_pdf_success():
    """Test successful PDF text extraction."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("src.parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content\n\nPage 2 content"
        mock_reader.return_value.pages = [mock_page, mock_page]

        result = await parser.parse(paper)

    assert result.parsed_text is not None
    assert "Page 1 content" in result.parsed_text
    assert result.status == PaperStatus.parsed


@pytest.mark.asyncio
async def test_parse_pdf_cleans_text():
    """Test that parser cleans excessive whitespace."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("src.parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Text  \n  \n  \nMore text   \n\n\n"
        mock_reader.return_value.pages = [mock_page]

        result = await parser.parse(paper)

    # Should collapse multiple blank lines
    assert "\n\n\n" not in result.parsed_text


@pytest.mark.asyncio
async def test_parse_pdf_missing_file():
    """Test handling when PDF file doesn't exist."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/nonexistent/2401.12345.pdf"),
    )

    result = await parser.parse(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_parse_pdf_encrypted():
    """Test handling encrypted/password-protected PDFs."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("src.parser.PdfReader") as mock_reader:
        mock_reader.side_effect = Exception("PDF is encrypted")

        result = await parser.parse(paper)

    assert result.status == PaperStatus.failed


@pytest.mark.asyncio
async def test_parse_empty_pdf():
    """Test handling PDF with no extractable text."""
    parser = PDFParser()

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/fake/path/2401.12345.pdf"),
    )

    with patch("src.parser.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader.return_value.pages = [mock_page]

        result = await parser.parse(paper)

    # Should still succeed, just use abstract as text
    assert result.status == PaperStatus.parsed
    assert result.parsed_text == paper.abstract
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_parser.py -v`
Expected: FAIL with import errors

**Step 3: Implement parser.py**

Create `src/parser.py`:

```python
"""PDF text extraction module."""

import re
from pathlib import Path

from pypdf import PdfReader

from src.models import Paper, PaperStatus


class PDFParser:
    """Extracts text content from PDF files."""

    async def parse(self, paper: Paper) -> Paper:
        """Extract text from paper's PDF file."""
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            reader = PdfReader(str(paper.pdf_path))
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            if text_parts:
                full_text = "\n\n".join(text_parts)
                # Clean up excessive whitespace
                full_text = re.sub(r"\n{3,}", "\n\n", full_text)
                full_text = re.sub(r" +", " ", full_text)
                paper.parsed_text = full_text.strip()
            else:
                # Fallback to abstract if no text extracted
                paper.parsed_text = paper.abstract

            paper.status = PaperStatus.parsed
            return paper

        except Exception as e:
            # Mark as failed on any parsing error
            paper.status = PaperStatus.failed
            return paper
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_parser.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/parser.py tests/unit/test_parser.py
git commit -m "feat: add PDF parser module"
```

---

## Task 8: LLM Summarizer Module

**Files:**
- Create: `src/summarizer.py`
- Create: `prompts/summary_template.md`
- Create: `prompts/summary_zh.md`
- Test: `tests/unit/test_summarizer.py`

**Step 1: Create prompt templates**

Create `prompts/summary_template.md`:

```markdown
You are a research paper summarization assistant. Analyze the following paper and provide a structured summary.

## Paper Information
**Title**: {paper_title}
**Abstract**: {abstract}
**Full Text**: {full_text}

## Instructions
Generate a structured summary in {language} with the following JSON format:
{{
  "research_problem": "What problem does this paper address?",
  "core_method": "What is the main method or approach?",
  "contributions": ["Key contribution 1", "Key contribution 2"],
  "experiments": "What experiments were conducted and what were the main results?",
  "limitations": "What are the limitations or future work?",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "applicable_scenarios": "When would this approach be useful?"
}}

Keep the summary {summary_level} and focused on technical details.
```

Create `prompts/summary_zh.md`:

```markdown
你是一个研究论文摘要助手。请分析以下论文并提供结构化摘要。

## 论文信息
**标题**: {paper_title}
**摘要**: {abstract}
**全文**: {full_text}

## 指令
请生成中文的结构化摘要，使用以下JSON格式：
{{
  "research_problem": "这篇论文解决了什么问题？",
  "core_method": "主要的方法或途径是什么？",
  "contributions": ["主要贡献1", "主要贡献2"],
  "experiments": "进行了什么实验？主要结果是什么？",
  "limitations": "有哪些局限性或未来工作？",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "applicable_scenarios": "这种方法在什么场景下有用？"
}}

保持摘要{summary_level}，专注于技术细节。
```

**Step 2: Write failing test for summarizer**

Create `tests/unit/test_summarizer.py`:

```python
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest
from src.config import ModelConfig
from src.models import Paper, PaperStatus
from src.summarizer import PaperSummarizer


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

    mock_response = AsyncMock()
    mock_response.choices = [type("Choice", (), {
        "message": type("Message", (), {
            "content": '{"research_problem": "Test problem", "core_method": "Test method"}'
        })()
    })()]

    with patch("src.summarizer.AsyncOpenAI") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

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

    with patch("src.summarizer.AsyncOpenAI"):
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

    with patch("src.summarizer.AsyncOpenAI") as mock_client:
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

    with patch("src.summarizer.AsyncOpenAI") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await summarizer.summarize(paper)

    assert result.status == PaperStatus.failed
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_summarizer.py -v`
Expected: FAIL with import errors

**Step 4: Implement summarizer.py**

Create `src/summarizer.py`:

```python
"""LLM-based paper summarization module."""

import json
import os
from pathlib import Path

from openai import AsyncOpenAI

from src.config import ModelConfig
from src.models import Paper, PaperStatus


class PaperSummarizer:
    """Summarizes papers using LLM."""

    def __init__(
        self,
        model_config: ModelConfig,
        language: str = "en",
        summary_level: str = "standard",
        prompts_dir: Path = Path("prompts"),
    ) -> None:
        """Initialize summarizer with configuration."""
        self.config = model_config
        self.language = language
        self.summary_level = summary_level
        self.prompts_dir = prompts_dir

    async def summarize(self, paper: Paper) -> Paper:
        """Generate summary for a paper."""
        if not paper.parsed_text:
            paper.status = PaperStatus.failed
            return paper

        try:
            # Create prompt
            prompt = self._create_prompt(paper)

            # Call LLM
            response_text = await self._call_llm(prompt)

            # Parse response
            summary = json.loads(response_text)
            paper.summary = summary
            paper.status = PaperStatus.summarized
            return paper

        except Exception:
            paper.status = PaperStatus.failed
            return paper

    def _create_prompt(self, paper: Paper) -> str:
        """Create prompt from template."""
        template_name = f"summary_{self.language}.md"
        template_path = self.prompts_dir / template_name

        if not template_path.exists():
            template_path = self.prompts_dir / "summary_template.md"

        with template_path.open() as f:
            template = f.read()

        # Truncate text if too long (simple version)
        max_chars = 15000
        text = paper.parsed_text[:max_chars]

        return template.format(
            paper_title=paper.title,
            abstract=paper.abstract,
            full_text=text,
            language=self.language,
            summary_level=self.summary_level,
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API with retry."""
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {self.config.api_key_env}")

        client_kwargs = {"api_key": api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        client = AsyncOpenAI(**client_kwargs)

        try:
            response = await client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content

        finally:
            await client.close()
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_summarizer.py -v`
Expected: PASS (5 tests)

**Step 6: Commit**

```bash
git add src/summarizer.py tests/unit/test_summarizer.py prompts/summary_template.md prompts/summary_zh.md
git commit -m "feat: add LLM summarizer module with prompt templates"
```

---

## Task 9: Markdown Renderer Module

**Files:**
- Create: `src/renderer.py`
- Test: `tests/unit/test_renderer.py`

**Step 1: Write failing test for renderer**

Create `tests/unit/test_renderer.py`:

```python
from datetime import datetime
from pathlib import Path
import pytest
from src.models import Paper, PaperStatus
from src.renderer import MarkdownRenderer


def test_render_basic_markdown(tmp_path):
    """Test basic Markdown rendering."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper Title",
        authors=["Alice Smith", "Bob Jones"],
        abstract="This is a test abstract describing the paper.",
        submitted_date=datetime(2024, 1, 15, 10, 30, 0),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
        parsed_text="Full text content...",
        summary={
            "research_problem": "Test problem description",
            "core_method": "Test method description",
            "contributions": ["Contribution 1", "Contribution 2"],
            "experiments": "Test experiments description",
            "limitations": "Test limitations",
            "keywords": ["AI", "machine learning", "transformers"],
            "applicable_scenarios": "Test scenarios",
        },
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    assert output_path.exists()
    content = output_path.read_text()

    # Verify key sections
    assert "# Test Paper Title" in content
    assert "Alice Smith" in content
    assert "Bob Jones" in content
    assert "2401.12345" in content
    assert "This is a test abstract" in content
    assert "Test problem description" in content
    assert "Test method description" in content
    assert "Contribution 1" in content
    assert "machine learning" in content


def test_render_creates_directory(tmp_path):
    """Test that renderer creates output directory."""
    output_dir = tmp_path / "summaries"
    renderer = MarkdownRenderer(output_dir=output_dir)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test",
        authors=["A"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/test.pdf",
        summary={"research_problem": "Test"},
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    assert output_dir.exists()
    assert output_path.parent == output_dir


def test_render_without_summary(tmp_path):
    """Test rendering paper without summary."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author"],
        abstract="Test abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        summary=None,
        status=PaperStatus.parsed,
    )

    output_path = renderer.render(paper)

    assert output_path.exists()
    content = output_path.read_text()
    assert "# Test Paper" in content
    assert "No summary available" in content


def test_render_sanitizes_filename(tmp_path):
    """Test that special characters in title are sanitized."""
    renderer = MarkdownRenderer(output_dir=tmp_path)

    paper = Paper(
        arxiv_id="2401.12345",
        title="Test/Paper: Special <Characters> & More!",
        authors=["Author"],
        abstract="Abstract",
        submitted_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        summary={"research_problem": "Test"},
        status=PaperStatus.summarized,
    )

    output_path = renderer.render(paper)

    # Filename should not contain special characters
    assert "/" not in output_path.name
    assert ":" not in output_path.name
    assert "<" not in output_path.name
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_renderer.py -v`
Expected: FAIL with import errors

**Step 3: Implement renderer.py**

Create `src/renderer.py`:

```python
"""Markdown generation module."""

import re
from datetime import datetime
from pathlib import Path

from src.models import Paper


class MarkdownRenderer:
    """Renders papers as Markdown documents."""

    def __init__(self, output_dir: Path) -> None:
        """Initialize renderer with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, paper: Paper) -> Path:
        """Render paper as Markdown file."""
        filename = self._sanitize_filename(f"{paper.arxiv_id}_{paper.title[:50]}")
        output_path = self.output_dir / f"{filename}.md"

        content = self._generate_content(paper)
        output_path.write_text(content)

        return output_path

    def _sanitize_filename(self, filename: str) -> str:
        """Remove special characters from filename."""
        # Replace special chars with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple spaces
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length
        return sanitized[:100]

    def _generate_content(self, paper: Paper) -> str:
        """Generate Markdown content."""
        lines = []

        # Title
        lines.append(f"# {paper.title}")
        lines.append("")

        # Metadata section
        lines.append("## Metadata")
        lines.append(f"- **arXiv ID**: {paper.arxiv_id}")
        lines.append(f"- **Authors**: {', '.join(paper.authors)}")
        lines.append(f"- **Submitted**: {paper.submitted_date.strftime('%Y-%m-%d')}")
        lines.append(f"- **Categories**: {', '.join(paper.categories)}")
        if paper.pdf_path:
            lines.append(f"- **PDF**: `{paper.pdf_path}`")
        lines.append(f"- **URL**: {paper.pdf_url}")
        lines.append("")

        # Abstract section
        lines.append("## Abstract")
        lines.append(paper.abstract)
        lines.append("")

        # Summary section (if available)
        if paper.summary:
            lines.append("## Summary")

            if "research_problem" in paper.summary:
                lines.append("### Research Problem")
                lines.append(paper.summary["research_problem"])
                lines.append("")

            if "core_method" in paper.summary:
                lines.append("### Core Method")
                lines.append(paper.summary["core_method"])
                lines.append("")

            if "contributions" in paper.summary:
                lines.append("### Contributions")
                for contribution in paper.summary["contributions"]:
                    lines.append(f"- {contribution}")
                lines.append("")

            if "experiments" in paper.summary:
                lines.append("### Experiments")
                lines.append(paper.summary["experiments"])
                lines.append("")

            if "limitations" in paper.summary:
                lines.append("### Limitations")
                lines.append(paper.summary["limitations"])
                lines.append("")

            if "keywords" in paper.summary:
                lines.append("### Keywords")
                for keyword in paper.summary["keywords"]:
                    lines.append(f"- {keyword}")
                lines.append("")

            if "applicable_scenarios" in paper.summary:
                lines.append("### Applicable Scenarios")
                lines.append(paper.summary["applicable_scenarios"])
                lines.append("")
        else:
            lines.append("## Summary")
            lines.append("*No summary available.*")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by Paper Daily on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_renderer.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/renderer.py tests/unit/test_renderer.py
git commit -m "feat: add Markdown renderer module"
```

---

## Task 10: Pipeline Runner Module

**Files:**
- Create: `src/runner.py`
- Test: `tests/integration/test_pipeline.py`

**Step 1: Write integration test for pipeline**

Create `tests/integration/test_pipeline.py`:

```python
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from src.config import Config
from src.runner import PipelineRunner


@pytest.mark.asyncio
async def test_pipeline_full_run(tmp_path):
    """Test full pipeline run with mocked components."""
    # Create test config
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

runtime:
  dry_run: false
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)

    runner = PipelineRunner(config)

    # Mock all external dependencies
    with patch("src.runner.ArXivFetcher") as mock_fetcher_class:
        with patch("src.runner.PDFDownloader") as mock_downloader_class:
            with patch("src.runner.PDFParser") as mock_parser_class:
                with patch("src.runner.PaperSummarizer") as mock_summarizer_class:
                    with patch("src.runner.MarkdownRenderer") as mock_renderer_class:

                        # Setup mocks
                        from src.models import Paper, PaperStatus

                        sample_paper = Paper(
                            arxiv_id="2401.12345",
                            title="Test Paper",
                            authors=["Author"],
                            abstract="Test abstract",
                            submitted_date=datetime.now(),
                            categories=["cs.AI"],
                            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
                        )

                        # Mock fetcher
                        mock_fetcher = AsyncMock()
                        mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])
                        mock_fetcher_class.return_value = mock_fetcher

                        # Mock downloader
                        mock_downloader = AsyncMock()
                        mock_downloader.download = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "pdf_path": tmp_path / "test.pdf", "status": PaperStatus.downloaded}
                            )
                        )
                        mock_downloader_class.return_value = mock_downloader

                        # Mock parser
                        mock_parser = AsyncMock()
                        mock_parser.parse = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "parsed_text": "Test text", "status": PaperStatus.parsed}
                            )
                        )
                        mock_parser_class.return_value = mock_parser

                        # Mock summarizer
                        mock_summarizer = AsyncMock()
                        mock_summarizer.summarize = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "summary": {"test": "data"}, "status": PaperStatus.summarized}
                            )
                        )
                        mock_summarizer_class.return_value = mock_summarizer

                        # Mock renderer
                        mock_renderer = MagicMock()
                        mock_output = tmp_path / "output.md"
                        mock_output.write_text("test")
                        mock_renderer.render = MagicMock(return_value=mock_output)
                        mock_renderer_class.return_value = mock_renderer

                        # Run pipeline
                        results = await runner.run()

    assert len(results["processed"]) >= 0
    assert "total" in results["metrics"]
    assert results["metrics"]["total"] == 1


@pytest.mark.asyncio
async def test_pipeline_dry_run(tmp_path):
    """Test pipeline dry run mode."""
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 2

runtime:
  dry_run: true

output:
  base_dir: {tmp_path / "data"}
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)
    runner = PipelineRunner(config)

    with patch("src.runner.ArXivFetcher") as mock_fetcher_class:
        from src.models import Paper

        sample_paper = Paper(
            arxiv_id="2401.12345",
            title="Test",
            authors=["A"],
            abstract="Abs",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/test.pdf",
        )

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])
        mock_fetcher_class.return_value = mock_fetcher

        results = await runner.run()

    # In dry run, should only fetch
    assert results["metrics"]["total"] == 1


@pytest.mark.asyncio
async def test_pipeline_skip_processed_papers(tmp_path):
    """Test that already processed papers are skipped."""
    # Similar setup with state manager having existing paper
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_pipeline.py -v`
Expected: FAIL with import errors

**Step 3: Implement runner.py**

Create `src/runner.py`:

```python
"""Pipeline orchestration module."""

import logging
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models import Paper, PaperStatus
from src.state_manager import StateManager
from src.fetcher import ArXivFetcher
from src.downloader import PDFDownloader
from src.parser import PDFParser
from src.summarizer import PaperSummarizer
from src.renderer import MarkdownRenderer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates the paper processing pipeline."""

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration."""
        self.config = config
        self.state = StateManager(Path("state/paper_state.json"))
        self.state.load()

        # Initialize modules
        self.fetcher = ArXivFetcher(config.query)
        self.downloader = PDFDownloader(
            base_dir=config.output.base_dir,
            retry_times=config.runtime.retry_times,
            timeout_sec=config.runtime.timeout_sec,
        )
        self.parser = PDFParser()
        self.summarizer = PaperSummarizer(
            model_config=config.model,
            language=config.pipeline.language,
            summary_level=config.pipeline.summary_level,
        )
        self.renderer = MarkdownRenderer(
            output_dir=config.output.base_dir / "summaries"
        )

    async def run(self) -> dict:
        """Execute the pipeline."""
        logger.info("Starting paper pipeline run")
        start_time = datetime.now()

        # Fetch papers
        papers = await self.fetcher.fetch()
        logger.info(f"Fetched {len(papers)} papers from arXiv")

        # Filter out already processed papers
        new_papers = [p for p in papers if not self.state.is_paper_processed(p.arxiv_id)]
        logger.info(f"{len(new_papers)} new papers to process")

        if self.config.runtime.dry_run:
            logger.info("Dry run mode - skipping processing")
            return {
                "processed": [],
                "failed": [],
                "metrics": {
                    "total": len(papers),
                    "new": len(new_papers),
                    "processed": 0,
                    "failed": 0,
                    "duration_seconds": 0,
                },
            }

        processed = []
        failed = []

        for paper in new_papers:
            try:
                # Download
                if self.config.pipeline.download_pdf:
                    paper = await self.downloader.download(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status, pdf_path=paper.pdf_path)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Parse
                if self.config.pipeline.parse_pdf:
                    paper = await self.parser.parse(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Summarize
                if self.config.pipeline.summarize:
                    paper = await self.summarizer.summarize(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Render
                if self.config.pipeline.output_markdown:
                    markdown_path = self.renderer.render(paper)
                    self.state.update_paper_status(
                        paper.arxiv_id, paper.status, markdown_path=markdown_path
                    )

                processed.append(paper.arxiv_id)
                logger.info(f"Successfully processed {paper.arxiv_id}")

            except Exception as e:
                logger.error(f"Error processing {paper.arxiv_id}: {e}")
                self.state.update_paper_status(paper.arxiv_id, PaperStatus.failed, error=str(e))
                if not self.config.runtime.continue_on_error:
                    raise
                failed.append(paper.arxiv_id)

        # Save state
        self.state.update_last_run()
        self.state.save()

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "processed": processed,
            "failed": failed,
            "metrics": {
                "total": len(papers),
                "new": len(new_papers),
                "processed": len(processed),
                "failed": len(failed),
                "duration_seconds": duration,
            },
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_pipeline.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/runner.py tests/integration/test_pipeline.py
git commit -m "feat: add pipeline runner orchestrator"
```

---

## Task 11: CLI Entry Point

**Files:**
- Create: `main.py`
- Create: `README.md`

**Step 1: Create main.py**

Create `main.py`:

```python
"""CLI entry point for Paper Daily."""

import asyncio
import sys
from pathlib import Path

import typer

from src.config import Config

app = typer.Typer()


@app.command()
def main(
    config: Path = typer.Option(Path("config/config.yaml"), "--config", help="Path to config file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run without downloading/processing"),
    max_papers: int | None = typer.Option(None, "--max-papers", help="Maximum number of papers to process"),
    retry_failed: bool = typer.Option(False, "--retry-failed", help="Retry previously failed papers"),
):
    """Run the paper pipeline."""
    # Load config
    if not config.exists():
        typer.echo(f"Config file not found: {config}", err=True)
        sys.exit(1)

    cfg = Config.from_yaml(config)

    # Override config with CLI options
    if dry_run:
        cfg.runtime.dry_run = True
    if max_papers:
        cfg.query.max_results = max_papers

    # Import here to avoid circular imports
    from src.runner import PipelineRunner

    async def run():
        runner = PipelineRunner(cfg)
        results = await runner.run()

        # Print results
        typer.echo(f"\n=== Pipeline Results ===")
        typer.echo(f"Total papers found: {results['metrics']['total']}")
        typer.echo(f"New papers: {results['metrics']['new']}")
        typer.echo(f"Successfully processed: {results['metrics']['processed']}")
        typer.echo(f"Failed: {results['metrics']['failed']}")
        typer.echo(f"Duration: {results['metrics']['duration_seconds']:.1f}s")

        if results["failed"]:
            typer.echo(f"\nFailed papers: {', '.join(results['failed'])}")

    asyncio.run(run())


if __name__ == "__main__":
    app()
```

**Step 2: Update pyproject.toml with typer dependency**

Edit `pyproject.toml`, add to dependencies:
```toml
dependencies = [
    "arxiv>=2.0.0",
    "httpx>=0.27.0",
    "pypdf>=3.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0",
    "openai>=1.0.0",
    "typer>=0.12.0",  # Add this line
]
```

**Step 3: Create README.md**

Create `README.md`:

```markdown
# Paper Daily

Automated paper retrieval, analysis, and summarization system.

## Features

- Fetch papers from arXiv by keywords and categories
- Download PDFs automatically
- Extract text content
- Generate AI-powered summaries using Deepseek
- Output structured Markdown documents
- Track processing state to avoid duplicates

## Installation

```bash
# Install dependencies
uv pip install -e .

# Set Deepseek API key
export DEEPSEEK_API_KEY="your-api-key"
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
query:
  keywords: ["your keywords here"]
  max_results: 10

pipeline:
  language: zh  # or en
  summary_level: standard

model:
  provider: deepseek
  api_key_env: DEEPSEEK_API_KEY
```

## Usage

```bash
# Basic usage
paper-daily --config config.yaml

# Dry run (no downloads)
paper-daily --config config.yaml --dry-run

# Limit papers
paper-daily --config config.yaml --max-papers 5
```

## Output

- `data/pdfs/` - Downloaded PDF files
- `data/summaries/` - Generated Markdown summaries
- `state/paper_state.json` - Processing state
- `logs/pipeline.log` - Run logs
```

**Step 4: Run full test suite**

Run: `pytest tests/ -v --cov=src --cov-report=term-missing`

**Step 5: Install typer**

Run: `uv pip install typer`

**Step 6: Commit**

```bash
git add main.py README.md pyproject.toml
git commit -m "feat: add CLI entry point and documentation"
```

---

## Task 12: Final Integration Test

**Step 1: Run complete test suite**

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Check coverage target (should be >=80%)
```

**Step 2: Test CLI with dry run**

```bash
# Test dry run mode
paper-daily --config config/config.yaml --dry-run
```

**Step 3: Verify all directories created**

```bash
ls -la config/ data/ logs/ prompts/ state/ src/ tests/
```

**Step 4: Run linter**

```bash
ruff check src/ tests/
```

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete AutoPaper Pipeline MVP implementation"
```

---

## Success Criteria Checklist

The MVP is complete when:

- [ ] All unit tests pass (≥80% coverage)
- [ ] Integration tests pass
- [ ] CLI runs without errors in dry-run mode
- [ ] Directory structure matches design
- [ ] All modules are implemented and tested
- [ ] State persistence works correctly
- [ ] Error handling doesn't crash pipeline
- [ ] Markdown output is generated correctly
