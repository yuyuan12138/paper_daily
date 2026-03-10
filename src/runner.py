"""Pipeline orchestration module."""

import logging
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models import PaperStatus
from src.state_manager import StateManager
from src.fetcher import ArXivFetcher
from src.downloader import PDFDownloader
from src.parser import PDFParser
from src.summarizer import PaperSummarizer
from src.renderer import MarkdownRenderer
from src.image_extractor import ImageExtractor
from src.image_analyzer import ImageAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates the paper processing pipeline."""

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration."""
        self.config = config
        self.state = StateManager(Path("state/paper_state.json"))
        self.state.load()

        # Initialize modules
        self.fetcher = ArXivFetcher(config.query)
        self.downloader = PDFDownloader(
            base_dir=config.output.base_dir,
            retry_times=config.runtime.retry_times,
            timeout_sec=config.runtime.timeout_sec,
        )
        self.parser = PDFParser()
        self.summarizer = PaperSummarizer(
            model_config=config.model,
            language=config.pipeline.language,
            summary_level=config.pipeline.summary_level,
        )
        self.renderer = MarkdownRenderer(
            output_dir=config.output.base_dir / "summaries"
        )

        # Initialize image modules if enabled
        if config.vision.enabled:
            self.image_extractor = ImageExtractor(
                min_size=config.vision.extraction.min_size,
                max_aspect_ratio=config.vision.extraction.max_aspect_ratio,
                max_images_per_paper=config.vision.extraction.max_images_per_paper,
                skip_duplicates=config.vision.extraction.skip_duplicates,
                output_dir=config.vision.storage.output_dir,
            )
            self.image_analyzer = ImageAnalyzer(
                provider=config.vision.analysis.provider,
                model_name=config.vision.analysis.model_name,
                api_key_env=config.vision.analysis.api_key_env,
                base_url=config.vision.analysis.base_url,
                max_tokens=config.vision.analysis.max_tokens,
                batch_size=config.vision.analysis.batch_size,
            )
        else:
            self.image_extractor = None
            self.image_analyzer = None

    async def run(self) -> dict:
        """Execute the pipeline."""
        logger.info("Starting paper pipeline run")
        start_time = datetime.now()

        # Fetch papers
        papers = await self.fetcher.fetch()
        logger.info(f"Fetched {len(papers)} papers from arXiv")

        # Filter out already processed papers
        new_papers = [p for p in papers if not self.state.is_paper_processed(p.arxiv_id)]
        logger.info(f"{len(new_papers)} new papers to process")

        if self.config.runtime.dry_run:
            logger.info("Dry run mode - skipping processing")
            return {
                "processed": [],
                "failed": [],
                "metrics": {
                    "total": len(papers),
                    "new": len(new_papers),
                    "processed": 0,
                    "failed": 0,
                    "duration_seconds": 0,
                },
            }

        processed = []
        failed = []

        for paper in new_papers:
            try:
                # Download
                if self.config.pipeline.download_pdf:
                    paper = await self.downloader.download(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status, pdf_path=paper.pdf_path)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Parse
                if self.config.pipeline.parse_pdf:
                    paper = await self.parser.parse(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Extract and analyze images
                if self.config.vision.enabled and self.config.pipeline.parse_pdf:
                    try:
                        paper = await self.image_extractor.extract(paper)
                        self.state.update_paper_status(paper.arxiv_id, paper.status)

                        if paper.images and self.config.vision.analysis:
                            paper = await self.image_analyzer.analyze(paper)
                            self.state.update_paper_status(paper.arxiv_id, paper.status)
                    except Exception as e:
                        logger.warning(f"Image processing failed for {paper.arxiv_id}: {e}")
                        # Continue with text-only summary

                # Summarize
                if self.config.pipeline.summarize:
                    paper = await self.summarizer.summarize(paper)
                    self.state.update_paper_status(paper.arxiv_id, paper.status)

                    if paper.status == PaperStatus.failed:
                        failed.append(paper.arxiv_id)
                        continue

                # Render
                if self.config.pipeline.output_markdown:
                    markdown_path = self.renderer.render(paper)
                    self.state.update_paper_status(
                        paper.arxiv_id, paper.status, markdown_path=markdown_path
                    )

                processed.append(paper.arxiv_id)
                logger.info(f"Successfully processed {paper.arxiv_id}")

            except Exception as e:
                logger.error(f"Error processing {paper.arxiv_id}: {e}")
                self.state.update_paper_status(paper.arxiv_id, PaperStatus.failed, error=str(e))
                if not self.config.runtime.continue_on_error:
                    raise
                failed.append(paper.arxiv_id)

        # Save state
        self.state.update_last_run()
        self.state.save()

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "processed": processed,
            "failed": failed,
            "metrics": {
                "total": len(papers),
                "new": len(new_papers),
                "processed": len(processed),
                "failed": len(failed),
                "duration_seconds": duration,
            },
        }
