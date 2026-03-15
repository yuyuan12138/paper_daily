"""LLM-based paper summarization module."""

import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from config import ModelConfig
from models import Paper, PaperStatus

logger = logging.getLogger(__name__)

# Step name to prompt file mapping
STEP_PROMPTS = {
    "screening": "step1_screening_{lang}.md",
    "quick": "step2_quick_{lang}.md",
    "deep": "step3_deep_{lang}.md",
    "experiments": "step4_experiments_{lang}.md",
    "reproducibility": "step5_reproducibility_{lang}.md",
    "inspiration": "step6_inspiration_{lang}.md",
}


class PaperSummarizer:
    """Summarizes papers using LLM."""

    def __init__(
        self,
        model_config: ModelConfig,
        language: str = "en",
        summary_level: str = "standard",
        prompts_dir: Path = Path("prompts"),
        multi_step_enabled: bool = False,
        multi_step_steps: list[str] = None,
    ) -> None:
        """Initialize summarizer with configuration."""
        self.config = model_config
        self.language = language
        self.summary_level = summary_level
        self.prompts_dir = prompts_dir
        self.multi_step_enabled = multi_step_enabled
        self.multi_step_steps = multi_step_steps or ["screening", "quick", "deep", "experiments"]

    async def summarize(self, paper: Paper) -> Paper:
        """Generate summary for a paper."""
        if not paper.parsed_text:
            logger.warning("No parsed text available for summarization: %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

        try:
            if self.multi_step_enabled:
                # Multi-step analysis
                summary = await self._multi_step_summarize(paper)
            else:
                # Single-step analysis
                summary = await self._single_step_summarize(paper)

            paper.summary = summary
            paper.status = PaperStatus.summarized
            return paper

        except Exception as e:
            logger.exception("Failed to summarize paper %s: %s", paper.arxiv_id, e)
            paper.status = PaperStatus.failed
            return paper

    async def _single_step_summarize(self, paper: Paper) -> dict:
        """Single-step summarization (original method)."""
        prompt = self._create_prompt(paper)
        logger.info("Calling LLM for summarization: %s", paper.arxiv_id)
        response_text = await self._call_llm(prompt)
        return self._parse_json_response(response_text)

    async def _multi_step_summarize(self, paper: Paper) -> dict:
        """Multi-step analysis (multiple API calls)."""
        summary = {}

        for step in self.multi_step_steps:
            logger.info(f"Step {step}: Processing {paper.arxiv_id}")

            # Get prompt template for this step
            prompt = await self._create_step_prompt(paper, step)

            # Call LLM
            response_text = await self._call_llm(prompt)

            # Parse response
            step_result = self._parse_json_response(response_text)
            summary[step] = step_result

            logger.info(f"Step {step}: Completed for {paper.arxiv_id}")

        return summary

    async def _create_step_prompt(self, paper: Paper, step: str) -> str:
        """Create prompt for a specific step."""
        # Get prompt file name
        lang = self.language
        prompt_file = STEP_PROMPTS.get(step, f"step_{step}_{{lang}}.md").format(lang=lang)
        prompt_path = self.prompts_dir / prompt_file

        # Fallback to template if specific file doesn't exist
        if not prompt_path.exists():
            prompt_path = self.prompts_dir / f"summary_{lang}.md"

        with prompt_path.open() as f:
            template = f.read()

        # Prepare paper info
        paper_info = self._format_paper_info(paper)

        return template.format(
            paper_title=paper.title,
            abstract=paper.abstract,
            full_text=paper.parsed_text[:15000],
            paper_info=paper_info,
            research_interest="大型语言模型",  # Could be configurable
        )

    def _format_paper_info(self, paper: Paper) -> str:
        """Format paper metadata and abstract for prompts."""
        return f"""标题: {paper.title}
作者: {', '.join(paper.authors)}
分类: {', '.join(paper.categories)}
摘要: {paper.abstract}"""

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response."""
        json_text = response_text.strip()
        if json_text.startswith("```"):
            parts = json_text.split("```")
            for part in parts[1:]:
                if part.strip().startswith("json"):
                    json_text = part[4:]
                elif part.strip().startswith("{"):
                    json_text = part
                json_text = json_text.strip()
                try:
                    return json.loads(json_text)
                except:
                    continue

        return json.loads(json_text)

    def _create_prompt(self, paper: Paper) -> str:
        """Create prompt from template."""
        template_name = f"summary_{self.language}.md"
        template_path = self.prompts_dir / template_name

        if not template_path.exists():
            template_path = self.prompts_dir / "summary_template.md"

        with template_path.open() as f:
            template = f.read()

        # Truncate text if too long (simple version)
        max_chars = 15000
        text = paper.parsed_text[:max_chars]

        return template.format(
            paper_title=paper.title,
            abstract=paper.abstract,
            full_text=text,
            language=self.language,
            summary_level=self.summary_level,
            images_context="",
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API with retry."""
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            logger.error("API key not found for environment variable: %s", self.config.api_key_env)
            raise ValueError(f"API key not found: {self.config.api_key_env}")

        logger.debug("Using API key from: %s", self.config.api_key_env)

        client_kwargs = {"api_key": api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        client = AsyncOpenAI(**client_kwargs)

        try:
            response = await client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content

        finally:
            await client.close()
