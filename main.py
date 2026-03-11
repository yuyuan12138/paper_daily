"""CLI entry point for Paper Daily."""

import asyncio
import sys
from pathlib import Path

import typer

from config import Config

app = typer.Typer()


async def run_pipeline(cfg: Config):
    """Run the pipeline asynchronously."""
    from runner import PipelineRunner

    runner = PipelineRunner(cfg)
    return await runner.run()


@app.command()
def run(
    config: Path = typer.Option(Path("config/config.yaml"), "--config", "-c", help="Path to config file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run without downloading/processing"),
    max_papers: int | None = typer.Option(None, "--max-papers", "-n", help="Maximum number of papers to process"),
    retry_failed: bool = typer.Option(False, "--retry-failed", help="Retry previously failed papers"),
):
    """Run the paper pipeline."""
    # Load config
    if not config.exists():
        typer.echo(f"Config file not found: {config}", err=True)
        sys.exit(1)

    cfg = Config.from_yaml(config)

    # Override config with CLI options
    if dry_run:
        cfg.runtime.dry_run = True
    if max_papers:
        cfg.query.max_results = max_papers

    # Run pipeline
    results = asyncio.run(run_pipeline(cfg))

    # Print results
    typer.echo("\n=== Pipeline Results ===")
    typer.echo(f"Total papers found: {results['metrics']['total']}")
    typer.echo(f"New papers: {results['metrics']['new']}")
    typer.echo(f"Successfully processed: {results['metrics']['processed']}")
    typer.echo(f"Failed: {results['metrics']['failed']}")
    typer.echo(f"Duration: {results['metrics']['duration_seconds']:.1f}s")

    if results["failed"]:
        typer.echo(f"\nFailed papers: {', '.join(results['failed'])}")


@app.command()
def cleanup(
    state_file: Path = typer.Option(Path("state/paper_state.json"), "--state", "-s", help="Path to state file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned without actually cleaning"),
):
    """Clean up invalid state entries (missing PDFs or markdown files)."""
    from state_manager import StateManager

    state = StateManager(state_file)
    state.load()

    # Scan for invalid entries
    papers_to_remove = []
    for arxiv_id, entry in state.state["papers"].items():
        removed_reason = None

        # Check markdown for summarized papers
        if entry.get("status") == "summarized":
            markdown_path = entry.get("markdown_path")
            if markdown_path and not Path(markdown_path).exists():
                removed_reason = f"missing markdown: {markdown_path}"
            else:
                pdf_path = entry.get("pdf_path")
                if pdf_path and not Path(pdf_path).exists():
                    removed_reason = f"missing PDF: {pdf_path}"

        # Check PDF for downloaded papers
        elif entry.get("status") in ["downloaded", "parsed", "images_extracted"]:
            pdf_path = entry.get("pdf_path")
            if pdf_path and not Path(pdf_path).exists():
                removed_reason = f"missing PDF: {pdf_path}"

        if removed_reason:
            papers_to_remove.append((arxiv_id, removed_reason))
            typer.echo(f"  {arxiv_id}: {removed_reason}")

    if dry_run:
        typer.echo(f"\nWould remove {len(papers_to_remove)} invalid entries (dry-run)")
    else:
        for arxiv_id, _ in papers_to_remove:
            del state.state["papers"][arxiv_id]
        state.save()
        typer.echo(f"\nCleaned {len(papers_to_remove)} invalid entries")


@app.command()
def invalidate(
    arxiv_id: str = typer.Argument(..., help="arXiv ID to invalidate"),
    state_file: Path = typer.Option(Path("state/paper_state.json"), "--state", "-s", help="Path to state file"),
):
    """Invalidate a specific paper's status, forcing reprocessing."""
    from state_manager import StateManager

    state = StateManager(state_file)
    state.load()

    if arxiv_id in state.state["papers"]:
        del state.state["papers"][arxiv_id]
        state.save()
        typer.echo(f"Invalidated: {arxiv_id}")
    else:
        typer.echo(f"Paper not found in state: {arxiv_id}", err=True)
        sys.exit(1)


# Keep backward compatibility: if no subcommand, run pipeline
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Path = typer.Option(Path("config/config.yaml"), "--config", "-c", help="Path to config file", show_default=False),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run without downloading/processing"),
    max_papers: int | None = typer.Option(None, "--max-papers", "-n", help="Maximum number of papers to process"),
    retry_failed: bool = typer.Option(False, "--retry-failed", help="Retry previously failed papers"),
):
    """Paper Daily - arXiv paper processing pipeline."""
    # If no subcommand is provided, run the pipeline
    if ctx.invoked_subcommand is None:
        # Load config
        if not config.exists():
            typer.echo(f"Config file not found: {config}", err=True)
            sys.exit(1)

        cfg = Config.from_yaml(config)

        # Override config with CLI options
        if dry_run:
            cfg.runtime.dry_run = True
        if max_papers:
            cfg.query.max_results = max_papers

        # Run pipeline
        results = asyncio.run(run_pipeline(cfg))

        # Print results
        typer.echo("\n=== Pipeline Results ===")
        typer.echo(f"Total papers found: {results['metrics']['total']}")
        typer.echo(f"New papers: {results['metrics']['new']}")
        typer.echo(f"Successfully processed: {results['metrics']['processed']}")
        typer.echo(f"Failed: {results['metrics']['failed']}")
        typer.echo(f"Duration: {results['metrics']['duration_seconds']:.1f}s")

        if results["failed"]:
            typer.echo(f"\nFailed papers: {', '.join(results['failed'])}")


if __name__ == "__main__":
    app()
