# Design: Paper Image Extraction and Analysis Feature

**Date:** 2026-03-10
**Feature:** Image Extraction & Multimodal Analysis
**Status:** Approved

---

## 1. Overview

Add image extraction and multimodal LLM analysis to the AutoPaper pipeline. Extract figures, tables, and charts from PDFs, analyze them using vision-capable LLMs, and embed figure descriptions in the generated summaries.

## 2. Architecture

### 2.1 Pipeline Flow

```
Current: fetcher → downloader → parser → summarizer → renderer
Extended: fetcher → downloader → parser → [image_extractor → image_analyzer] → summarizer → renderer
```

### 2.2 New Modules

| Module | Responsibility |
|--------|---------------|
| `ImageExtractor` | Extract images from PDF using PyMuPDF, apply smart filters |
| `ImageAnalyzer` | Analyze images with multimodal LLM (OpenAI/Anthropic) |

---

## 3. Data Model

### 3.1 New Fields

```python
class ImageMetadata:
    path: Path              # Path to saved image
    page_number: int        # Source page in PDF
    figure_number: str | None  # Extracted from caption
    caption: str | None     # Associated caption text
    analysis: ImageAnalysis | None
    image_type: str         # "figure" | "table" | "chart" | "unknown"

class ImageAnalysis:
    description: str        # Visual description
    key_findings: list[str] # Important insights
    relevance: str          # "high" | "medium" | "low"
```

### 3.2 Updated PaperStatus

```python
class PaperStatus(Enum):
    discovered = "discovered"
    downloaded = "downloaded"
    parsed = "parsed"
    images_extracted = "images_extracted"   # NEW
    images_analyzed = "images_analyzed"     # NEW
    summarized = "summarized"
    failed = "failed"
```

---

## 4. Component Design

### 4.1 ImageExtractor

- Uses `PyMuPDF` (fitz) for image extraction
- Smart filtering:
  - Skip images < 200x200px
  - Skip aspect ratios < 0.3 or > 3.0
  - Skip header/footer regions (top/bottom 10%)
  - Detect and skip duplicates via perceptual hash
  - Max 20 images per paper
- Saves to `data/images/{arxiv_id}/figure_{page}_{idx}.png`

### 4.2 ImageAnalyzer

- Configurable provider (OpenAI GPT-4o or Anthropic Claude)
- Batch processing (default 5 images per call)
- Prompt includes: paper title, caption, surrounding text context
- Returns structured JSON with type, description, key findings, relevance

### 4.3 Updated Summarizer

- Summarizer receives image analyses in context
- Prompts updated to include figure references
- Embeds figure descriptions in relevant sections

---

## 5. Configuration

```yaml
vision:
  enabled: true
  extraction:
    min_size: [200, 200]
    max_aspect_ratio: 3.0
    max_images_per_paper: 20
    skip_duplicates: true
  analysis:
    provider: openai
    model_name: gpt-4o
    api_key_env: OPENAI_API_KEY
    base_url: null
    max_tokens: 1000
    batch_size: 5
  storage:
    output_dir: ./data/images
```

---

## 6. Error Handling

| Scenario | Handling |
|----------|----------|
| PDF not image-extractable | Log warning, continue with text only |
| LLM vision unavailable | Store images without analysis |
| Rate limit hit | Exponential backoff, retry |
| Disk full | Skip remaining images, cleanup temp |

**Graceful degradation:** Pipeline always produces a summary, even if images fail.

---

## 7. Dependencies

```toml
pymupdf = ">=1.24.0"   # PDF image extraction
pillow = ">=10.0.0"    # Image processing
anthropic = ">=0.40.0"  # Claude API
```

---

## 8. Implementation Phases

1. **Phase 1:** Image extraction (no LLM) - 2-3 days
2. **Phase 2:** Image analysis with vision API - 2-3 days
3. **Phase 3:** Summary integration - 1-2 days
4. **Phase 4:** Testing & polish - 2-3 days

---

## 9. Backward Compatibility

- `vision.enabled: false` (default) → existing behavior unchanged
- Missing vision config → defaults to disabled
- Image failures → text-only summary still generated
