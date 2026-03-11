# PDFFigures2 集成设计文档

**日期**: 2025-03-11
**作者**: Claude Code
**状态**: 设计阶段

## 概述

将 pdffigures2（Scala-based PDF 图表提取工具）集成到 paper_daily 项目中，替换现有的 PyMuPDF 图片提取器。pdffigures2 提供更精确的图表检测、标题识别和 Figure/Table 分类能力。

## 设计决策

| 决策点 | 选择 | 说明 |
|--------|------|------|
| 集成方式 | 完全替换 | 使用 pdffigures2 替换现有 PyMuPDF 提取器 |
| 调用方式 | 编译 JAR | 预先编译 JAR 文件，通过 subprocess 调用 |
| 输出命名 | 简化命名 | Figure1.png, Table1.png 格式 |
| 配置方式 | YAML 配置 | 在 config.yaml 中新增 pdffigures2 配置段 |
| 架构方案 | 方案 A | 创建新的 PDFFigures2Extractor 类，保持代码解耦 |

## 架构设计

### 文件结构

```
src/
├── image_extractor.py       # 现有的 PyMuPDF 提取器（保留备用）
├── pdffigures_extractor.py  # 新的 pdffigures2 提取器
├── extractor_factory.py     # 工厂类，根据配置选择提取器
├── config.py                # 扩展配置支持 pdffigures2
└── runner.py                # 更新主流程使用工厂
```

### 类设计

#### PDFFigures2Extractor

```python
class PDFFigures2Extractor:
    """使用 pdffigures2 JAR 提取 PDF 中的图表"""

    def __init__(
        self,
        jar_path: Path,              # pdffigures2 JAR 文件路径
        output_dir: Path,            # 图片输出目录
        dpi: int = 150,              # 渲染 DPI
        extract_figures: bool = True,  # 是否提取 Figure
        extract_tables: bool = True,   # 是否提取 Table
        max_figures: int = 20,       # 最大提取数量
        java_options: list = None    # Java 选项（如内存设置）
    )

    async def extract(self, paper: Paper) -> Paper:
        """提取图表并返回带图片元数据的 Paper 对象"""

    def _run_pdffigures2(self, pdf_path: Path, temp_dir: Path) -> list:
        """运行 JAR 并返回解析的 JSON 数据"""

    def _parse_figure_data(self, fig_data: dict, arxiv_id: str) -> ImageMetadata:
        """将 pdffigures2 JSON 转换为 ImageMetadata"""

    def _rename_image(self, old_path: Path, new_path: Path) -> Path:
        """重命名图片文件为简化格式"""
```

#### ExtractorFactory

```python
class ExtractorFactory:
    """根据配置创建图片提取器实例"""

    @staticmethod
    def create(config: dict) -> ImageExtractor | PDFFigures2Extractor:
        """根据配置返回相应的提取器实例"""
```

## 数据流设计

```
Paper (with PDF)
       |
       v
PDFFigures2Extractor.extract()
       |
       v
创建临时目录
       |
       v
运行: java -jar pdffigures2.jar <pdf> -m <temp/img> -d <temp/data>
       |
       v
解析 JSON 输出文件
       |
       v
重命名图片文件到 data/images/{arxiv_id}/
   - figures_output{arxiv_id}-Figure1-1.png → Figure1.png
   - figures_output{arxiv_id}-Table1-1.png → Table1.png
       |
       v
构建 ImageMetadata 对象
   - path: 图片路径
   - page_number: 页码
   - figure_number: 图表编号
   - caption: 标题文本
   - fig_type: "Figure" 或 "Table"
       |
       v
清理临时目录
       |
       v
Paper.images[] (填充完成)
```

## 配置设计

### config.yaml 新增配置段

```yaml
pdffigures2:
  enabled: true              # 是否启用 pdffigures2
  jar_path: /path/to/pdffigures2.jar  # JAR 文件路径
  dpi: 150                   # 渲染 DPI
  extract_figures: true      # 是否提取 Figure
  extract_tables: true       # 是否提取 Table
  max_figures: 20            # 最大提取数量
  java_options:
    - "-Xmx2g"               # 最大堆内存 2GB
    - "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider"
```

### 现有 vision 配置调整

```yaml
vision:
  enabled: true
  extractor: pdffigures2     # 新增: "pymupdf" 或 "pdffigures2"
  extraction:
    min_size: [100, 100]
    max_aspect_ratio: 5.0
    max_images_per_paper: 15
```

## pdffigures2 JSON 输出格式

```json
{
  "caption": "Figure 1: Overview of the framework.",
  "captionBoundary": {"x1": 70.8, "x2": 524.4, "y1": 301.7, "y2": 331.6},
  "figType": "Figure",
  "imageText": ["AI", "safety", ...],
  "name": "1",
  "page": 1,
  "regionBoundary": {"x1": 97.9, "x2": 495.3, "y1": 73.4, "y2": 296.1},
  "renderDpi": 150,
  "renderURL": "figures_output2603.08486-Figure1-1.png"
}
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| JAR 文件不存在 | PaperStatus.failed, 记录错误日志 |
| Java 未安装 | PaperStatus.failed, 友好的错误提示 |
| PDF 损坏无法解析 | 跳过该 PDF，记录警告 |
| JSON 解析失败 | 回退到原始文件名，记录警告 |
| 图片重命名失败 | 保留原文件名，继续处理 |
| 提取超时 | 终止进程，记录超时 |

## 测试策略

1. **正常流程测试**: JAR 调用成功 → 正确提取图片和元数据
2. **JSON 解析测试**: 正确转换为 ImageMetadata
3. **图片重命名测试**: 文件名格式正确
4. **配置加载测试**: 正确读取 YAML 配置
5. **JAR 不存在测试**: 优雅降级
6. **PDF 无图片测试**: 返回空列表
7. **Figure/Table 分类测试**: figType 正确识别

## pdffigures2 JAR 编译

```bash
cd pdffigures2
sbt assembly
# 输出: target/scala-2.13/pdffigures2-assembly-*.jar
```

## 实施步骤

1. 创建 `src/pdffigures_extractor.py`
2. 创建 `src/extractor_factory.py`
3. 更新 `src/config.py` 添加 pdffigures2 配置解析
4. 更新 `src/runner.py` 使用工厂创建提取器
5. 更新 `src/models.py` 添加 fig_type 字段
6. 更新 `src/renderer.py` 支持 Figure/Table 分类显示
7. 编写单元测试
8. 更新 README.md 文档

## 向后兼容

- 保留现有的 `ImageExtractor` 类
- 通过 `vision.extractor` 配置项选择提取器
- 默认值为 `pymupdf`，需要显式配置才使用 pdffigures2
