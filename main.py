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
def main(
    config: Path = typer.Option(Path("config/config.yaml"), "--config", help="Path to config file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run without downloading/processing"),
    max_papers: int | None = typer.Option(None, "--max-papers", help="Maximum number of papers to process"),
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


if __name__ == "__main__":
    app()
