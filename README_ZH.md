# Paper Daily

自动化论文检索、分析和摘要生成系统。

## 功能特性

- 根据关键词和分类从 arXiv 获取论文
- 自动下载 PDF 文件
- 从 PDF 中提取文本内容
- **从论文中提取图片并附带标题**（支持 PyMuPDF 或 PDFFigures2）
- **使用多模态 AI 分析图片**（通过 SiliconFlow 使用 QwenVL）
- 使用 DeepSeek（或 OpenAI/Anthropic）生成 AI 摘要
- 输出结构化的 Markdown 文档
- 跟踪处理状态并验证文件完整性
- **并发 API 调用**加速处理

## 安装

### 1. 安装依赖

```bash
# 安装项目依赖
uv pip install -e .
```

### 2. 设置 API 密钥

您需要至少一个 LLM API 密钥：

```bash
# 用于摘要生成（推荐使用 DeepSeek）
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# 用于图片分析（使用 SiliconFlow 的 QwenVL）
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```

**获取 API 密钥：**
- DeepSeek: https://platform.deepseek.com/
- SiliconFlow: https://cloud.siliconflow.cn/

### 3.（可选）编译 PDFFigures2

更好的图片提取（带标题）：

```bash
cd pdffigures2
sbt assembly
```

## 配置

编辑 `config/config.yaml`：

```yaml
# arXiv 查询设置
query:
  keywords: ["large language model"]
  categories: []
  max_results: 10

# 管道设置
pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true
  language: zh  # 或 en
  summary_level: standard

# 视觉（图片提取和分析）
vision:
  enabled: true
  extractor: pdffigures2  # 或 "pymupdf"

  # PDFFigures2 设置
  pdffigures2_jar: "/path/to/pdffigures2.jar"
  pdffigures2_dpi: 150
  pdffigures2_extract_figures: true
  pdffigures2_extract_tables: true
  pdffigures2_max_figures: 20

  # 图片分析（多模态 LLM）- 可选
  analysis:
    enabled: false  # 设为 true 启用
    provider: "openai-compatible"
    model_name: "Qwen/Qwen3-VL-30B-A3B-Instruct"
    api_key_env: "SILICONFLOW_API_KEY"
    base_url: "https://api.siliconflow.cn/v1"
    max_tokens: 2000
    max_concurrency: 5  # 并发 API 调用数

  storage:
    output_dir: ./data/images

# 摘要模型
model:
  provider: deepseek
  base_url: "https://api.deepseek.com/v1"
  model_name: "deepseek-chat"
  api_key_env: DEEPSEEK_API_KEY
  temperature: 0.2
  max_tokens: 4000
  max_concurrency: 5  # 并发 API 调用数
```

### 配置选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `query.keywords` | 搜索关键词 | `["large language model"]` |
| `query.max_results` | 每次运行最大论文数 | `10` |
| `pipeline.language` | 摘要语言 | `zh` |
| `vision.enabled` | 启用图片提取 | `false` |
| `vision.extractor` | 图片提取器 | `pymupdf` |
| `vision.analysis.enabled` | 启用图片分析（⚠️开发中） | `false` |
| `vision.analysis.max_concurrency` | 最大并发 API 调用 | `5` |
| `model.max_concurrency` | 最大并发摘要 | `5` |

> ⚠️ **注意**：图片分析功能（`vision.analysis.enabled`）目前处于开发阶段，可能产生不一致的结果。建议暂时保持关闭状态。

## 使用方法

### 基本用法

```bash
# 运行管道（使用环境变量或命令前缀）
DEEPSEEK_API_KEY=xxx uv run main.py

# 或使用 SiliconFlow 进行图片分析
DEEPSEEK_API_KEY=xxx SILICONFLOW_API_KEY=xxx uv run main.py
```

### 命令行选项

```bash
# 处理最多论文数
uv run main.py --max-papers 5

# 试运行（不下载/处理）
uv run main.py --dry-run

# 自定义配置
uv run main.py --config path/to/config.yaml
```

### 管理命令

```bash
# 清理无效状态条目（文件缺失）
uv run main.py cleanup

# 预览清理但不删除
uv run main.py cleanup --dry-run

# 使论文状态无效（强制重新处理）
uv run main.py invalidate 2603.09964
```

## 输出

```
data/
├── pdfs/           # 下载的 PDF 文件
├── summaries/      # 生成的 Markdown 摘要
│   └── {arxiv_id}_{title}.md
└── images/        # 提取的图片
    └── {arxiv_id}/
        ├── Figure1.png
        └── Table1.png
```

### 摘要格式

生成的 Markdown 包括：

- **元数据**：arXiv ID、作者、日期、分类
- **摘要**：论文原始摘要
- **摘要**（AI 生成）：
  - 单步模式：研究问题、核心方法、贡献、实验、局限性、关键词、适用场景、图表
  - 多步模式：
    - 粗筛：核心问题、主要贡献、创新点、相关性、潜在风险、阅读建议
    - 粗读：研究问题、假设、方法总览、模型IO、实验设置、主要结果、局限性
    - 精读：方法流程、核心模块、设计理由、新增部分、假设、性能来源
    - 实验分析：核心论点、实验对齐、baseline质量、消融实验、最强/弱证据
- **图表**：带标题的图片

### 多步骤分析

在 `config.yaml` 中启用详细的多步骤分析：

```yaml
pipeline:
  multi_step_enabled: true
  multi_step_steps:
    - screening    # 粗筛 - 初步筛选
    - quick        # 粗读 - 快速阅读
    - deep        # 精读 - 深入分析
    - experiments  # 实验分析 - 实验分析
    # - reproducibility  # 复现/落地
    # - inspiration     # 研究启发
```

每个步骤会单独调用 API 进行更详细的分析。

## 环境要求

- Python 3.13+
- uv（包管理器）
- Java 11+（用于 PDFFigures2）
- LLM 提供商的 API 密钥

## 许可证

MIT
