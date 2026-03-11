"""Image analysis module using multimodal LLMs."""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from models import Paper, PaperStatus, ImageMetadata, ImageAnalysis

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Analyzes images from papers using multimodal LLM APIs."""

    def __init__(
        self,
        provider: str = "openai-compatible",
        model_name: str = "Qwen/Qwen2-VL-7B-Instruct",
        api_key_env: str = "SILICONFLOW_API_KEY",
        base_url: str | None = "https://api.siliconflow.cn/v1",
        max_tokens: int = 2000,
        batch_size: int = 5,
        max_concurrency: int = 5,
    ) -> None:
        """Initialize the image analyzer.

        Args:
            provider: LLM provider - "openai", "anthropic", or "openai-compatible"
            model_name: Model to use for analysis
            api_key_env: Environment variable name for API key
            base_url: Optional base URL for API (for compatible providers)
            max_tokens: Maximum tokens in response
            batch_size: Number of images to process in each batch
            max_concurrency: Maximum number of concurrent API calls
        """
        self.provider = provider
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency

    async def analyze(self, paper: Paper) -> Paper:
        """Analyze all images in a paper.

        Args:
            paper: The paper with images to analyze.

        Returns:
            The paper with analyzed images.
        """
        # If paper has no images, set status and return
        if not paper.images:
            paper.status = PaperStatus.images_analyzed
            return paper

        try:
            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def analyze_with_semaphore(img: ImageMetadata) -> ImageMetadata:
                """Analyze single image with semaphore."""
                async with semaphore:
                    try:
                        analysis = await self._analyze_single_image(paper, img)
                        img.analysis = analysis
                        return img
                    except Exception as e:
                        logger.warning(
                            "Failed to analyze image %s for paper %s: %s",
                            img.path,
                            paper.arxiv_id,
                            e,
                        )
                        return img

            # Process all images concurrently with limited concurrency
            results = await asyncio.gather(
                *[analyze_with_semaphore(img) for img in paper.images],
                return_exceptions=True,
            )

            # Check if any image was successfully analyzed
            any_success = any(
                isinstance(r, ImageMetadata) and r.analysis is not None
                for r in results
            )

            # If at least one image was analyzed successfully, mark as analyzed
            if any_success:
                paper.status = PaperStatus.images_analyzed
            else:
                # All images failed, graceful degradation
                paper.status = PaperStatus.images_extracted
            return paper

        except Exception:
            logger.exception("Failed to analyze images for paper %s", paper.arxiv_id)
            # On error, set status to images_extracted (graceful degradation)
            paper.status = PaperStatus.images_extracted
            return paper

    async def _analyze_batch(self, paper: Paper, images: list[ImageMetadata]) -> bool:
        """Analyze a batch of images.

        Args:
            paper: The paper containing the images.
            images: List of images to analyze.

        Returns:
            True if at least one image was analyzed successfully.
        """
        any_success = False
        for img in images:
            try:
                analysis = await self._analyze_single_image(paper, img)
                img.analysis = analysis
                any_success = True
            except Exception as e:
                logger.warning(
                    "Failed to analyze image %s for paper %s: %s",
                    img.path,
                    paper.arxiv_id,
                    e,
                )
                # Continue with next image
        return any_success

    async def _analyze_single_image(
        self, paper: Paper, img: ImageMetadata
    ) -> ImageAnalysis:
        """Analyze a single image.

        Args:
            paper: The paper containing the image.
            img: The image metadata.

        Returns:
            ImageAnalysis results.
        """
        # Read image as base64
        image_base64 = self._read_image_as_base64(img.path)

        # Call appropriate LLM based on provider
        if self.provider == "openai" or self.provider == "openai-compatible":
            return await self._analyze_with_openai(paper, img, image_base64)
        elif self.provider == "anthropic":
            return await self._analyze_with_anthropic(paper, img, image_base64)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _analyze_with_openai(
        self, paper: Paper, img: ImageMetadata, image_base64: str
    ) -> ImageAnalysis:
        """Analyze image using OpenAI API.

        Args:
            paper: The paper containing the image.
            img: The image metadata.
            image_base64: Base64-encoded image data.

        Returns:
            ImageAnalysis results.
        """
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {self.api_key_env}")

        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**client_kwargs)

        try:
            prompt = self._create_analysis_prompt(paper, img)

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            return self._parse_analysis_response(content)

        finally:
            await client.close()

    async def _analyze_with_anthropic(
        self, paper: Paper, img: ImageMetadata, image_base64: str
    ) -> ImageAnalysis:
        """Analyze image using Anthropic API.

        Args:
            paper: The paper containing the image.
            img: The image metadata.
            image_base64: Base64-encoded image data.

        Returns:
            ImageAnalysis results.
        """
        from anthropic import AsyncAnthropic

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {self.api_key_env}")

        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncAnthropic(**client_kwargs)

        try:
            prompt = self._create_analysis_prompt(paper, img)

            response = await client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64,
                                },
                            },
                        ],
                    }
                ],
            )

            content = response.content[0].text
            return self._parse_analysis_response(content)

        finally:
            await client.close()

    def _create_analysis_prompt(self, paper: Paper, img: ImageMetadata) -> str:
        """Create prompt for image analysis.

        Args:
            paper: The paper containing the image.
            img: The image metadata.

        Returns:
            Analysis prompt string.
        """
        prompt = f"""Analyze this image from the research paper "{paper.title}".

"""
        if img.caption:
            prompt += f"Image caption: {img.caption}\n"

        prompt += """Provide a detailed analysis in JSON format with the following fields:
- image_type: The type of image (e.g., "chart", "diagram", "photo", "table", "graph", "plot")
- description: A detailed description of what the image shows
- key_findings: List of key findings or observations from the image (1-3 items)
- relevance: How relevant this image is to understanding the paper's contribution ("high", "medium", or "low")

Respond only with valid JSON in this format:
{
    "image_type": "...",
    "description": "...",
    "key_findings": ["...", "..."],
    "relevance": "..."
}
"""
        return prompt

    def _parse_analysis_response(self, content: str) -> ImageAnalysis:
        """Parse LLM response into ImageAnalysis.

        Args:
            content: Raw response content from LLM.

        Returns:
            ImageAnalysis object.
        """
        # Try to extract JSON from response
        try:
            # Find JSON block (between ```json and ``` or just curly braces)
            content = content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Find the JSON block
                start = content.find("```json")
                if start == -1:
                    start = content.find("```")
                end = content.rfind("```")
                if start != -1 and end != -1:
                    # Skip the opening fence
                    start = content.find("\n", start) + 1
                    content = content[start:end].strip()

            # Parse JSON
            data = json.loads(content)

            return ImageAnalysis(
                description=data.get("description", ""),
                key_findings=data.get("key_findings", []),
                relevance=data.get("relevance", "medium"),
            )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse analysis response as JSON: %s", e)
            # Return default analysis on parse failure
            return ImageAnalysis(
                description="Failed to analyze image",
                key_findings=[],
                relevance="low",
            )

    def _read_image_as_base64(self, image_path: Path) -> str:
        """Read image file and encode as base64.

        Args:
            image_path: Path to image file.

        Returns:
            Base64-encoded image string.
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


__all__ = ["ImageAnalyzer"]
