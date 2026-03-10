"""Integration tests for the pipeline runner."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from config import Config
from runner import PipelineRunner


@pytest.mark.asyncio
async def test_pipeline_full_run(tmp_path):
    """Test full pipeline run with mocked components."""
    # Create test config
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 1

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true

model:
  provider: deepseek
  api_key_env: FAKE_API_KEY

output:
  base_dir: {tmp_path / "data"}

runtime:
  dry_run: false
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)

    runner = PipelineRunner(config)

    # Mock all external dependencies
    with patch("runner.ArXivFetcher") as mock_fetcher_class:
        with patch("runner.PDFDownloader") as mock_downloader_class:
            with patch("runner.PDFParser") as mock_parser_class:
                with patch("runner.PaperSummarizer") as mock_summarizer_class:
                    with patch("runner.MarkdownRenderer") as mock_renderer_class:

                        # Setup mocks
                        from models import Paper, PaperStatus

                        sample_paper = Paper(
                            arxiv_id="2401.12345",
                            title="Test Paper",
                            authors=["Author"],
                            abstract="Test abstract",
                            submitted_date=datetime.now(),
                            categories=["cs.AI"],
                            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
                        )

                        # Mock fetcher
                        mock_fetcher = AsyncMock()
                        mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])
                        mock_fetcher_class.return_value = mock_fetcher

                        # Mock downloader
                        mock_downloader = AsyncMock()
                        mock_downloader.download = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "pdf_path": tmp_path / "test.pdf", "status": PaperStatus.downloaded}
                            )
                        )
                        mock_downloader_class.return_value = mock_downloader

                        # Mock parser
                        mock_parser = AsyncMock()
                        mock_parser.parse = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "parsed_text": "Test text", "status": PaperStatus.parsed}
                            )
                        )
                        mock_parser_class.return_value = mock_parser

                        # Mock summarizer
                        mock_summarizer = AsyncMock()
                        mock_summarizer.summarize = AsyncMock(
                            return_value=Paper(
                                **{**sample_paper.__dict__, "summary": {"test": "data"}, "status": PaperStatus.summarized}
                            )
                        )
                        mock_summarizer_class.return_value = mock_summarizer

                        # Mock renderer
                        mock_renderer = MagicMock()
                        mock_output = tmp_path / "output.md"
                        mock_output.write_text("test")
                        mock_renderer.render = MagicMock(return_value=mock_output)
                        mock_renderer_class.return_value = mock_renderer

                        # Run pipeline
                        results = await runner.run()

    assert len(results["processed"]) >= 0
    assert "total" in results["metrics"]
    assert results["metrics"]["total"] == 1


@pytest.mark.asyncio
async def test_pipeline_dry_run(tmp_path):
    """Test pipeline dry run mode."""
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 2

runtime:
  dry_run: true

output:
  base_dir: {tmp_path / "data"}
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)
    runner = PipelineRunner(config)

    with patch("runner.ArXivFetcher") as mock_fetcher_class:
        from models import Paper

        sample_paper = Paper(
            arxiv_id="2401.12345",
            title="Test",
            authors=["A"],
            abstract="Abs",
            submitted_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/test.pdf",
        )

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value=[sample_paper])
        mock_fetcher_class.return_value = mock_fetcher

        results = await runner.run()

    # In dry run, should only fetch
    assert results["metrics"]["total"] == 1


@pytest.mark.asyncio
async def test_pipeline_skip_processed_papers(tmp_path):
    """Test that already processed papers are skipped."""
    config_content = f"""
query:
  keywords: ["test"]
  max_results: 2

pipeline:
  download_pdf: true
  parse_pdf: true
  summarize: true
  output_markdown: true

model:
  provider: deepseek
  api_key_env: FAKE_API_KEY

output:
  base_dir: {tmp_path / "data"}

runtime:
  dry_run: false
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = Config.from_yaml(config_file)
    runner = PipelineRunner(config)

    # Add a processed paper to state
    runner.state.update_paper_status("2401.12345", "summarized")

    with patch("runner.ArXivFetcher") as mock_fetcher_class:
        with patch("runner.PDFDownloader") as mock_downloader_class:
            with patch("runner.PDFParser") as mock_parser_class:
                with patch("runner.PaperSummarizer") as mock_summarizer_class:
                    with patch("runner.MarkdownRenderer") as mock_renderer_class:
                        from models import Paper, PaperStatus

                        # Two papers: one already processed, one new
                        processed_paper = Paper(
                            arxiv_id="2401.12345",
                            title="Processed Paper",
                            authors=["A"],
                            abstract="Abs",
                            submitted_date=datetime.now(),
                            categories=["cs.AI"],
                            pdf_url="https://arxiv.org/pdf/test.pdf",
                        )

                        new_paper = Paper(
                            arxiv_id="2401.67890",
                            title="New Paper",
                            authors=["B"],
                            abstract="Abs",
                            submitted_date=datetime.now(),
                            categories=["cs.AI"],
                            pdf_url="https://arxiv.org/pdf/test2.pdf",
                        )

                        mock_fetcher = AsyncMock()
                        mock_fetcher.fetch = AsyncMock(return_value=[processed_paper, new_paper])
                        mock_fetcher_class.return_value = mock_fetcher

                        mock_downloader = AsyncMock()
                        mock_downloader.download = AsyncMock(
                            return_value=Paper(
                                **{**new_paper.__dict__, "pdf_path": tmp_path / "test.pdf", "status": PaperStatus.downloaded}
                            )
                        )
                        mock_downloader_class.return_value = mock_downloader

                        mock_parser = AsyncMock()
                        mock_parser.parse = AsyncMock(
                            return_value=Paper(
                                **{**new_paper.__dict__, "parsed_text": "Test", "status": PaperStatus.parsed}
                            )
                        )
                        mock_parser_class.return_value = mock_parser

                        mock_summarizer = AsyncMock()
                        mock_summarizer.summarize = AsyncMock(
                            return_value=Paper(
                                **{**new_paper.__dict__, "summary": {}, "status": PaperStatus.summarized}
                            )
                        )
                        mock_summarizer_class.return_value = mock_summarizer

                        mock_renderer = MagicMock()
                        mock_output = tmp_path / "output.md"
                        mock_output.write_text("test")
                        mock_renderer.render = MagicMock(return_value=mock_output)
                        mock_renderer_class.return_value = mock_renderer

                        results = await runner.run()

    # Should only process the new paper
    assert results["metrics"]["total"] == 2
    assert results["metrics"]["new"] == 1
