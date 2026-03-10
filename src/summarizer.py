"""LLM-based paper summarization module."""

import json
import os
from pathlib import Path

from openai import AsyncOpenAI

from config import ModelConfig
from models import Paper, PaperStatus


class PaperSummarizer:
    """Summarizes papers using LLM."""

    def __init__(
        self,
        model_config: ModelConfig,
        language: str = "en",
        summary_level: str = "standard",
        prompts_dir: Path = Path("prompts"),
    ) -> None:
        """Initialize summarizer with configuration."""
        self.config = model_config
        self.language = language
        self.summary_level = summary_level
        self.prompts_dir = prompts_dir

    async def summarize(self, paper: Paper) -> Paper:
        """Generate summary for a paper."""
        if not paper.parsed_text:
            paper.status = PaperStatus.failed
            return paper

        try:
            # Create prompt
            prompt = self._create_prompt(paper)

            # Call LLM
            response_text = await self._call_llm(prompt)

            # Parse response
            summary = json.loads(response_text)
            paper.summary = summary
            paper.status = PaperStatus.summarized
            return paper

        except Exception:
            paper.status = PaperStatus.failed
            return paper

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
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API with retry."""
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {self.config.api_key_env}")

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
