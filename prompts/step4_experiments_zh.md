# 实验分析提示词

请从批判性阅读角度分析这篇论文的实验部分。

## 论文信息

**标题**: {paper_title}

**摘要**: {abstract}

**正文**: {full_text}

请输出以下JSON格式：
```json
{{
  "core_claims": ["作者想通过实验验证的核心claim1", "claim2"],
  "experiment_alignment": [
    {{
      "experiment": "实验名称",
      "claim_supported": "支持的论点",
      "adequacy": "是否充分（是/否）及原因"
    }}
  ],
  "baseline_quality": "baseline是否合理，是否强？",
  "dataset_match": "数据集和评测指标是否匹配研究问题？",
  "ablation_adequacy": "ablation是否足够？缺了什么关键对照？",
  "strongest_evidence": "结果中最有说服力的证据是什么？",
  "weakest_evidence": "结果中最可疑或解释不充分的地方是什么？",
  "reviewer_questions": ["审稿人问题1", "问题2", "问题3"]
}}
```

要求：
- 不要只复述表格结果
- 重点分析"证据链是否闭合"
- 如果某个结论没有被充分支持，请明确指出
