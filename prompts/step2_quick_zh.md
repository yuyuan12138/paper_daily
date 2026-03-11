# 粗读提示词

请根据论文信息，把这篇论文拆解成一个适合快速阅读的结构化笔记。

## 论文信息

**标题**: {paper_title}

**摘要**: {abstract}

**正文**: {full_text}

请输出以下JSON格式：
```json
{{
  "research_question": "研究问题",
  "hypothesis": "论文假设或动机",
  "method_overview": "方法总览",
  "model_io": "模型/系统输入输出",
  "experiment_setup": "实验设置概览",
  "main_results": "主要结果",
  "claimed_advantages": "作者声称的优势",
  "limitations": "论文的主要局限",
  "recommended_sections": "如果只有10分钟，最值得看哪几节"
}}
```

要求：
- 用简洁学术语言
- 优先提炼逻辑主线
- 不要编造论文中没有的细节
- 如果某部分在原文不清楚，请直接指出
