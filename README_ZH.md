# Paper Daily 🚀

> 你的私人AI科研助手，轻松追踪最新论文！

## ✨ 功能特性

- 🔍 **智能搜索** - 根据关键词和分类从arXiv获取论文
- 📥 **自动下载** - 自动下载PDF文件
- 📖 **文本提取** - 从PDF中提取文本内容
- 🖼️ **图片提取** - 提取图表并附带标题（PyMuPDF或PDFFigures2）
- 🤖 **AI分析** - 使用多模态LLM分析图片（SiliconFlow QwenVL）
- 📝 **智能摘要** - AI生成摘要（DeepSeek、OpenAI、Anthropic）
- 📄 **Markdown输出** - 优美的结构化文档
- 🔐 **状态跟踪** - 文件完整性验证
- ⚡ **并发处理** - 并行API调用，加速处理

## 🚀 快速开始

### 1. 安装

```bash
uv pip install -e .
```

### 2. 设置API密钥

```bash
# 摘要生成（推荐DeepSeek）
export DEEPSEEK_API_KEY="your-key"

# 图片分析（SiliconFlow QwenVL）
export SILICONFLOW_API_KEY="your-key"
```

> 📚 获取密钥：[DeepSeek](https://platform.deepseek.com/) | [SiliconFlow](https://cloud.siliconflow.cn/)

### 3.（可选）PDFFigures2 安装

更好的图片提取（带标题和表格检测）：

```bash
# 首先安装 Java 11+ 和 sbt
# macOS: brew install openjdk@11 sbt
# Ubuntu: apt install openjdk-11-jdk sbt

# 编译 pdffigures2
cd pdffigures2
sbt assembly

# 编译完成后生成: target/scala-2.13/pdffigures2-assembly-*.jar
```

然后更新 `config.yaml`：

```yaml
vision:
  enabled: true
  extractor: pdffigures2
  pdffigures2_jar: "./pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar"
```

## ⚙️ 配置

编辑 `config/config.yaml`：

```yaml
query:
  keywords: ["large language model"]
  max_results: 10

pipeline:
  language: zh  # 或 en
  multi_step_enabled: false  # 🔄 启用详细分析

vision:
  enabled: true
  extractor: pdffigures2
  pdffigures2_jar: "/path/to/pdffigures2.jar"

model:
  provider: deepseek
  max_concurrency: 5
```

### 配置选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `query.keywords` | 搜索关键词 | `["large language model"]` |
| `pipeline.language` | 摘要语言 | `zh` |
| `vision.enabled` | 启用图片提取 | `false` |
| `vision.analysis.enabled` | 启用图片分析 ⚠️ | `false` |
| `multi_step_enabled` | 多步骤分析 | `false` |

> ⚠️ **注意**：图片分析功能正在开发中，结果可能不稳定！

## 🎯 使用方法

```bash
# 基本运行
DEEPSEEK_API_KEY=xxx uv run main.py

# 启用图片分析
DEEPSEEK_API_KEY=xxx SILICONFLOW_API_KEY=xxx uv run main.py

# 限制论文数量
uv run main.py --max-papers 5

# 试运行
uv run main.py --dry-run
```

### 🛠️ 管理命令

```bash
# 清理无效条目
uv run main.py cleanup

# 强制重新处理论文
uv run main.py invalidate 2603.09964
```

## 📊 多步骤分析

在 `config.yaml` 中启用详细分析：

```yaml
pipeline:
  multi_step_enabled: true
  multi_step_steps:
    - screening    # 🔍 初步筛选
    - quick       # 📖 快速阅读
    - deep       # 🧠 深入分析
    - experiments # 🔬 实验分析
```

每个步骤 = 一次API调用 = 更详细的分析！🎉

## 📁 输出结构

```
data/
├── pdfs/           # 📄 下载的PDF文件
├── summaries/      # 📝 生成的Markdown
│   └── {id}_{title}.md
└── images/       # 🖼️ 提取的图片
    └── {id}/
        ├── Figure1.png
        └── Table1.png
```

## 🎨 摘要格式

```markdown
## 元数据
- arXiv ID、作者、日期...

## 摘要
原始摘要

## 摘要
- 🔍 粗筛: 核心问题、相关性、阅读建议
- 📖 粗读: 研究问题、方法概览、主要结果
- 🧠 精读: 技术细节、模块、设计理由
- 🔬 实验分析: 核心论点、baseline、证据

## 图表
![图片](path/to/image.png)
*图注*
```

## 🖥️ 环境要求

- Python 3.13+
- uv包管理器
- Java 11+（用于PDFFigures2）
- API密钥（DeepSeek/OpenAI/Anthropic）

## 📄 许可证

MIT 🎉
