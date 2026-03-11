# Paper Daily

Automated paper retrieval, analysis, and summarization system.

## Features

- Fetch papers from arXiv by keywords and categories
- Download PDFs automatically
- Extract text content from PDFs
- **Extract images from papers with captions**
- **Analyze images using multimodal AI**
- Generate AI-powered summaries using DeepSeek (or OpenAI/Anthropic)
- Output structured Markdown documents
- Track processing state to avoid duplicates

## Installation

```bash
# Install dependencies
uv pip install -e .

# Set DeepSeek API key
export DEEPSEEK_API_KEY="your-api-key"
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
query:
  keywords: ["large language model"]
  max_results: 10

pipeline:
  language: zh  # or en
  summary_level: standard

# Image extraction and analysis (optional)
vision:
  enabled: true
  extraction:
    min_size: [100, 100]
    max_aspect_ratio: 5.0
    max_images_per_paper: 15
  # For image analysis, use OpenAI or Anthropic:
  # analysis:
  #   provider: openai
  #   model_name: gpt-4o-mini
  #   api_key_env: OPENAI_API_KEY

model:
  provider: deepseek
  api_key_env: DEEPSEEK_API_KEY
```

### Vision/Image Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `vision.enabled` | Enable image extraction | `false` |
| `vision.extraction.min_size` | Minimum image size (width, height) | `(100, 100)` |
| `vision.extraction.max_aspect_ratio` | Skip very wide/tall images | `5.0` |
| `vision.extraction.max_images_per_paper` | Maximum images to extract | `15` |
| `vision.analysis` | Image analysis config (optional) | `null` |

### PDFFigures2 Integration

The project supports two image extraction backends:

1. **PyMuPDF (default)**: Fast Python-based extraction using PyMuPDF
2. **PDFFigures2**: More precise extraction with better caption detection and Figure/Table classification

#### Using PDFFigures2

First, compile the JAR:

```bash
cd pdffigures2
sbt assembly
```

Then configure in `config.yaml`:

```yaml
vision:
  enabled: true
  extractor: pdffigures2
  # REQUIRED: Update this path to your compiled pdffigures2 JAR file
  pdffigures2_jar: "/absolute/path/to/pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar"
```

**Benefits of PDFFigures2:**
- Better figure boundary detection
- Accurate caption extraction
- Automatic Figure/Table classification
- Handles multi-column layouts better

**Output naming:**
- PyMuPDF: `figure_{page}_{index}.png`
- PDFFigures2: `Figure1.png`, `Table1.png`, etc.

## Usage

```bash
# Basic usage
paper-daily --config config.yaml

# Dry run (no downloads)
paper-daily --config config.yaml --dry-run

# Limit papers
paper-daily --config config.yaml --max-papers 5
```

### With Image Extraction

```bash
# Extract images and include in summary
paper-daily --config config/test_vision.yaml
```

## Output

```
data/
├── pdfs/           # Downloaded PDF files
├── summaries/      # Generated Markdown summaries
└── images/        # Extracted images (when vision enabled)
    └── {arxiv_id}/
        ├── figure_1_0.png
        └── figure_3_1.png
```

### Summary Format

The generated Markdown includes:

- **Metadata**: arXiv ID, authors, date, categories
- **Abstract**: Original paper abstract
- **Summary** (AI-generated):
  - Research Problem
  - Core Method
  - Contributions
  - Experiments
  - Limitations
  - Keywords
  - Applicable Scenarios
  - **Figures** (if image extraction enabled)

## Requirements

- Python 3.13+
- uv (package manager)
- API key for LLM provider (DeepSeek, OpenAI, or Anthropic)

## License

MIT
