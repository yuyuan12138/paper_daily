# Paper Daily

Automated paper retrieval, analysis, and summarization system.

## Features

- Fetch papers from arXiv by keywords and categories
- Download PDFs automatically
- Extract text content from PDFs
- **Extract images from papers with captions** (using PyMuPDF or PDFFigures2)
- **Analyze images using multimodal AI** (QwenVL via SiliconFlow)
- Generate AI-powered summaries using DeepSeek (or OpenAI/Anthropic)
- Output structured Markdown documents
- Track processing state with file integrity verification
- **Concurrent API calls** for faster processing

## Installation

### 1. Install Dependencies

```bash
# Install project dependencies
uv pip install -e .
```

### 2. Set API Keys

You need at least one LLM API key:

```bash
# For summarization (DeepSeek - recommended)
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# For image analysis (SiliconFlow - supports QwenVL)
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```

**Get API Keys:**
- DeepSeek: https://platform.deepseek.com/
- SiliconFlow: https://cloud.siliconflow.cn/

### 3. (Optional) Compile PDFFigures2

For better image extraction with captions:

```bash
cd pdffigures2
sbt assembly
```

## Configuration

Edit `config/config.yaml`:

```yaml
# arXiv query settings
query:
  keywords: ["large language model"]
  categories: []
  max_results: 10

# Pipeline settings
pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true
  language: zh  # or en
  summary_level: standard

# Vision (image extraction and analysis)
vision:
  enabled: true
  extractor: pdffigures2  # or "pymupdf"

  # PDFFigures2 settings
  pdffigures2_jar: "/path/to/pdffigures2.jar"
  pdffigures2_dpi: 150
  pdffigures2_extract_figures: true
  pdffigures2_extract_tables: true
  pdffigures2_max_figures: 20

  # Image analysis (multimodal LLM) - optional
  analysis:
    enabled: false  # Set to true to enable
    provider: "openai-compatible"
    model_name: "Qwen/Qwen3-VL-30B-A3B-Instruct"
    api_key_env: "SILICONFLOW_API_KEY"
    base_url: "https://api.siliconflow.cn/v1"
    max_tokens: 2000
    max_concurrency: 5  # Concurrent API calls

  storage:
    output_dir: ./data/images

# Summarization model
model:
  provider: deepseek
  base_url: "https://api.deepseek.com/v1"
  model_name: "deepseek-chat"
  api_key_env: DEEPSEEK_API_KEY
  temperature: 0.2
  max_tokens: 4000
  max_concurrency: 5  # Concurrent API calls
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `query.keywords` | Search keywords | `["large language model"]` |
| `query.max_results` | Max papers per run | `10` |
| `pipeline.language` | Summary language | `zh` |
| `vision.enabled` | Enable image extraction | `false` |
| `vision.extractor` | Image extractor | `pymupdf` |
| `vision.analysis.enabled` | Enable image analysis (⚠️ in development) | `false` |
| `vision.analysis.max_concurrency` | Max concurrent API calls | `5` |
| `model.max_concurrency` | Max concurrent summarization | `5` |

> ⚠️ **Note**: Image analysis (`vision.analysis.enabled`) is currently in development and may produce inconsistent results. It is recommended to keep it disabled for now.

## Usage

### Basic Usage

```bash
# Run pipeline (use env vars or prefix commands)
DEEPSEEK_API_KEY=xxx uv run main.py

# Or with SiliconFlow for image analysis
DEEPSEEK_API_KEY=xxx SILICONFLOW_API_KEY=xxx uv run main.py
```

### Command Line Options

```bash
# Process max papers
uv run main.py --max-papers 5

# Dry run (no downloads/processing)
uv run main.py --dry-run

# Custom config
uv run main.py --config path/to/config.yaml
```

### Management Commands

```bash
# Clean up invalid state entries (missing files)
uv run main.py cleanup

# Preview cleanup without removing
uv run main.py cleanup --dry-run

# Invalidate a paper (force reprocessing)
uv run main.py invalidate 2603.09964
```

## Output

```
data/
├── pdfs/           # Downloaded PDF files
├── summaries/      # Generated Markdown summaries
│   └── {arxiv_id}_{title}.md
└── images/        # Extracted images
    └── {arxiv_id}/
        ├── Figure1.png
        └── Table1.png
```

### Summary Format

Generated Markdown includes:

- **Metadata**: arXiv ID, authors, date, categories
- **Abstract**: Original paper abstract
- **Summary** (AI-generated):
  - Single-step mode: Research Problem, Core Method, Contributions, Experiments, Limitations, Keywords, Applicable Scenarios, Figures
  - Multi-step mode:
    - 粗筛 (Screening): Core problem, contributions, innovation, relevance, potential risks, reading suggestion
    - 粗读 (Quick Reading): Research question, hypothesis, method overview, model I/O, experiments, results, limitations
    - 精读 (Deep Reading): Method pipeline, core modules, design rationale, novel parts, assumptions, performance sources
    - 实验分析 (Experiment Analysis): Core claims, experiment alignment, baseline quality, ablation, strongest/weaker evidence
- **Figures and Tables**: Images with captions

### Multi-Step Analysis

Enable detailed multi-step analysis in `config.yaml`:

```yaml
pipeline:
  multi_step_enabled: true
  multi_step_steps:
    - screening    # 粗筛 - Initial screening
    - quick        # 粗读 - Quick reading
    - deep        # 精读 - Deep analysis
    - experiments  # 实验分析 - Experiment analysis
    # - reproducibility  # 复现/落地
    # - inspiration     # 研究启发
```

Each step makes a separate API call for more detailed analysis.

## Requirements

- Python 3.13+
- uv (package manager)
- Java 11+ (for PDFFigures2)
- API key for LLM provider

## License

MIT
