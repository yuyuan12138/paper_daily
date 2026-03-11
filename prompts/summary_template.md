# Research Paper Summarization Prompt

You are a rigorous research assistant. Please analyze the following paper and provide a deep structured summary.

## Paper Information
**Title**: {paper_title}
**Abstract**: {abstract}
**Full Text**: {full_text}
{images_context}

## Analysis Requirements

Please output in the following JSON format:

```json
{{
  "research_problem": "What is the core problem this paper addresses? 1-2 sentences.",
  "motivation": "What is the hypothesis or motivation? Why did the authors choose this problem?",
  "core_method": "What is the core method? What is the overall pipeline?",
  "model_io": "Model/System input, output, and key operations",
  "contributions": [
    "Contribution 1: specific description",
    "Contribution 2: specific description",
    "Contribution 3: specific description"
  ],
  "experiments": {{
    "setup": "Experiment setup overview",
    "datasets": "Datasets used",
    "results": "Main results"
  }},
  "limitations": [
    "Limitation 1: specific description",
    "Limitation 2: specific description"
  ],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "applicable_scenarios": "What scenarios is this method suitable for?",
  "potential_risks": "Potential risks: engineering stacking? Insufficient experiments? Narrow problem setting? Unclear contributions?",
  "figures": "Description of figures in the paper, format: Figure X - brief description"
}}
```

## Key Requirements

1. **No empty praise** - Analyze pros and cons objectively
2. **Don't repeat the abstract** - Provide your own synthesis
3. **Point out potential risks** - e.g., insufficient experiments, weak baselines, generalization issues
4. **Distinguish facts from speculation** - Only state what is in the paper as facts
5. **Be concise** - Each field no more than 100 words
6. **Must include figures field** - Describe charts and figures in the paper
