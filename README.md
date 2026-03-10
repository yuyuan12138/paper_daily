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
