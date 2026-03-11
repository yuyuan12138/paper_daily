# Paper Daily 🚀

> Your personal AI research assistant for staying up-to-date with the latest papers!

## ✨ Features

- 🔍 **Smart Search** - Fetch papers from arXiv by keywords and categories
- 📥 **Auto Download** - Download PDFs automatically
- 📖 **Text Extraction** - Extract text content from PDFs
- 🖼️ **Image Extraction** - Extract figures & tables with captions (PyMuPDF or PDFFigures2)
- 🤖 **AI Analysis** - Analyze images using multimodal LLMs (QwenVL via SiliconFlow)
- 📝 **Smart Summaries** - Generate AI-powered summaries (DeepSeek, OpenAI, Anthropic)
- 📄 **Markdown Output** - Beautiful structured Markdown documents
- 🔐 **State Tracking** - File integrity verification
- ⚡ **Concurrent API** - Parallel processing for speed

## 🚀 Quick Start

### 1. Install

```bash
uv pip install -e .
```

### 2. Set API Keys

```bash
# For summarization (DeepSeek - recommended)
export DEEPSEEK_API_KEY="your-key"

# For image analysis (SiliconFlow - supports QwenVL)
export SILICONFLOW_API_KEY="your-key"
```

> 📚 Get your keys: [DeepSeek](https://platform.deepseek.com/) | [SiliconFlow](https://cloud.siliconflow.cn/)

### 3. (Optional) Compile PDFFigures2

Better image extraction with captions:

```bash
cd pdffsbt assembly
igures2
```

## ⚙️ Configuration

Edit `config/config.yaml`:

```yaml
query:
  keywords: ["large language model"]
  max_results: 10

pipeline:
  language: zh  # or en
  multi_step_enabled: false  # 🔄 Enable for detailed analysis

vision:
  enabled: true
  extractor: pdffigures2
  pdffigures2_jar: "/path/to/pdffigures2.jar"

model:
  provider: deepseek
  max_concurrency: 5
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `query.keywords` | Search keywords | `["large language model"]` |
| `pipeline.language` | Summary language | `zh` |
| `vision.enabled` | Enable image extraction | `false` |
| `vision.analysis.enabled` | Enable image analysis ⚠️ | `false` |
| `multi_step_enabled` | Multi-step analysis | `false` |

> ⚠️ **Note**: Image analysis is in development - results may vary!

## 🎯 Usage

```bash
# Basic run
DEEPSEEK_API_KEY=xxx uv run main.py

# With image analysis
DEEPSEEK_API_KEY=xxx SILICONFLOW_API_KEY=xxx uv run main.py

# Limit papers
uv run main.py --max-papers 5

# Dry run
uv run main.py --dry-run
```

### 🛠️ Management Commands

```bash
# Clean up invalid entries
uv run main.py cleanup

# Force reprocess a paper
uv run main.py invalidate 2603.09964
```

## 📊 Multi-Step Analysis

Enable detailed analysis in `config.yaml`:

```yaml
pipeline:
  multi_step_enabled: true
  multi_step_steps:
    - screening    # 🔍 Initial screening
    - quick        # 📖 Quick reading
    - deep         # 🧠 Deep analysis
    - experiments  # 🔬 Experiment analysis
```

Each step = one API call = more detailed insights! 🎉

## 📁 Output

```
data/
├── pdfs/           # 📄 Downloaded PDFs
├── summaries/      # 📝 Generated Markdown
│   └── {id}_{title}.md
└── images/        # 🖼️ Extracted images
    └── {id}/
        ├── Figure1.png
        └── Table1.png
```

## 🎨 Summary Format

```markdown
## Metadata
- arXiv ID, Authors, Date...

## Abstract
Original abstract

## Summary
- 🔍 粗筛: Core problem, relevance, reading suggestion
- 📖 粗读: Research question, method overview, results
- 🧠 精读: Technical details, modules, design rationale
- 🔬 实验分析: Claims, baselines, evidence

## Figures and Tables
![Image](path/to/image.png)
*Caption*
```

## 🖥️ Requirements

- Python 3.13+
- uv package manager
- Java 11+ (for PDFFigures2)
- API key (DeepSeek/OpenAI/Anthropic)

## 📄 License

MIT 🎉
