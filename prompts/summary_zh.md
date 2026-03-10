你是一个研究论文摘要助手。请分析以下论文并提供结构化摘要。

## 论文信息
**标题**: {paper_title}
**摘要**: {abstract}
**全文**: {full_text}
{images_context}

## 指令
请生成中文的结构化摘要，使用以下JSON格式：
{{
  "research_problem": "这篇论文解决了什么问题？",
  "core_method": "主要的方法或途径是什么？",
  "contributions": ["主要贡献1", "主要贡献2"],
  "experiments": "进行了什么实验？主要结果是什么？",
  "limitations": "有哪些局限性或未来工作？",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "applicable_scenarios": "这种方法在什么场景下有用？",
  "figures": "必须包含论文中提到的图表信息，格式：图X-描述"
}}

**重要**：必须包含figures字段，描述论文中提到的图表内容。
