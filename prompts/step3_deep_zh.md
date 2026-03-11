# 精读提示词

请深入分析这篇论文的方法部分，目标是帮助我真正理解其技术设计。

## 论文信息

**标题**: {paper_title}

**摘要**: {abstract}

**正文**: {full_text}

请输出以下JSON格式：
```json
{{
  "method_pipeline": "方法整体流程（用步骤描述）",
  "core_modules": ["核心模块1：功能描述", "核心模块2：功能描述"],
  "module_details": [
    {{
      "module": "模块名",
      "input": "输入",
      "output": "输出",
      "key_operations": "关键操作"
    }}
  ],
  "design_rationale": "作者为什么要这样设计，而不是采用更直接的方法？",
  "novel_parts": "与baseline相比，真正新增的部分是什么？",
  "assumptions": "该方法最依赖哪些前提假设？",
  "performance_sources": "哪些地方可能是性能提升的主要来源？哪些可能是辅助性改进？",
  "key_implementation": "如果让我复现，最关键的实现细节可能在哪些地方？"
}}
```

要求：
- 优先解释"因果关系"和"设计动机"
- 避免只重复论文措辞
- 如果涉及公式，请解释公式的变量意义
- 如果文中信息不足，请明确指出无法确定
