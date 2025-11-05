"""Main CLI for Research Graph Explorer."""

import asyncio
import json
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ..discovery.seed_generator import SeedGenerator
from ..discovery.frontier_explorer import FrontierExplorer
from ..infrastructure.config import get_config


console = Console()


@click.group()
def cli():
    """Research Graph Explorer - AI-powered paper discovery and analysis."""
    pass


@cli.command()
@click.argument("research_question")
@click.option("--max-papers", default=100, help="Maximum papers to discover")
@click.option("--num-seeds", default=10, help="Number of seed papers")
@click.option("--threshold", default=0.6, help="Relevance threshold (0-1)")
@click.option("--output", default=None, help="Output file (JSON)")
def discover(research_question: str, max_papers: int, num_seeds: int, threshold: float, output: str):
    """Discover papers for a research question.

    Example:
        rgx discover "What are the latest advances in transformer architectures?"
    """
    asyncio.run(_discover(research_question, max_papers, num_seeds, threshold, output))


async def _discover(
    research_question: str, max_papers: int, num_seeds: int, threshold: float, output: str
):
    """Internal discover function."""
    console.print("\n[bold cyan]Research Graph Explorer[/bold cyan]")
    console.print(f"[yellow]Research Question:[/yellow] {research_question}\n")

    # Validate config
    config = get_config()
    if not config.validate_keys():
        console.print("[bold red]Error:[/bold red] API keys not configured!")
        console.print("Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file")
        return

    # Step 1: Generate seeds
    console.print("[bold green]Step 1:[/bold green] Generating seed papers...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching for seed papers...", total=None)

        seed_gen = SeedGenerator()
        seeds = await seed_gen.generate_seeds(research_question, num_seeds=num_seeds)

        progress.update(task, completed=True)

    console.print(f"✓ Found [bold]{len(seeds)}[/bold] seed papers\n")

    # Show seed papers
    if seeds:
        table = Table(title="Seed Papers", show_header=True, header_style="bold magenta")
        table.add_column("Title", style="cyan", no_wrap=False, max_width=60)
        table.add_column("Year", justify="right", style="green")
        table.add_column("Relevance", justify="right", style="yellow")

        for paper in seeds[:5]:  # Show top 5
            table.add_row(
                paper.short_title,
                str(paper.year) if paper.year else "N/A",
                f"{paper.relevance_score:.2f}" if paper.relevance_score else "N/A",
            )

        console.print(table)
        console.print()

    # Step 2: Explore
    console.print("[bold green]Step 2:[/bold green] Exploring citation network...")
    console.print(f"Target: {max_papers} papers, Threshold: {threshold}\n")

    explorer = FrontierExplorer(research_question)
    relevant_papers = await explorer.explore(
        seed_papers=seeds, max_papers=max_papers, relevance_threshold=threshold
    )

    # Show results
    console.print(f"\n[bold green]✓ Discovery Complete![/bold green]")
    console.print(f"Found [bold]{len(relevant_papers)}[/bold] relevant papers\n")

    # Statistics
    stats = explorer.get_discovery_statistics()

    stats_table = Table(title="Discovery Statistics", show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Total Explored", str(stats["total_explored"]))
    stats_table.add_row("Relevant Papers", str(stats["total_relevant"]))
    stats_table.add_row("Relevance Rate", f"{stats['relevance_rate']:.1%}")
    stats_table.add_row("Avg Relevance", f"{stats['avg_relevance']:.2f}")

    console.print(stats_table)
    console.print()

    # Top papers
    if relevant_papers:
        papers_table = Table(title="Top 10 Papers", show_header=True, header_style="bold magenta")
        papers_table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
        papers_table.add_column("Year", justify="right", style="green")
        papers_table.add_column("Score", justify="right", style="yellow")
        papers_table.add_column("Citations", justify="right", style="blue")

        for paper in relevant_papers[:10]:
            papers_table.add_row(
                paper.short_title,
                str(paper.year) if paper.year else "N/A",
                f"{paper.relevance_score:.2f}" if paper.relevance_score else "N/A",
                str(paper.metadata.citation_count),
            )

        console.print(papers_table)
        console.print()

    # Save output
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "research_question": research_question,
            "statistics": stats,
            "papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "abstract": p.abstract,
                    "authors": [a.name for a in p.authors],
                    "year": p.year,
                    "relevance_score": p.relevance_score,
                    "relevance_reasoning": p.relevance_reasoning,
                    "citation_count": p.metadata.citation_count,
                    "venue": p.metadata.venue,
                    "doi": p.metadata.doi,
                    "arxiv_id": p.metadata.arxiv_id,
                    "pdf_url": str(p.metadata.pdf_url) if p.metadata.pdf_url else None,
                }
                for p in relevant_papers
            ],
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        console.print(f"[bold green]✓[/bold green] Saved results to [cyan]{output}[/cyan]")


@cli.command()
def config_check():
    """Check configuration and API keys."""
    console.print("\n[bold cyan]Configuration Check[/bold cyan]\n")

    config = get_config()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")

    # API Keys
    table.add_row(
        "Anthropic API Key",
        "Set" if config.anthropic_api_key else "Not set",
        "✓" if config.anthropic_api_key else "✗",
    )
    table.add_row(
        "OpenAI API Key",
        "Set" if config.openai_api_key else "Not set",
        "✓" if config.openai_api_key else "✗",
    )
    table.add_row(
        "Semantic Scholar API Key",
        "Set" if config.semantic_scholar_api_key else "Not set (optional)",
        "✓" if config.semantic_scholar_api_key else "○",
    )

    # Settings
    table.add_row("Default LLM", config.default_llm, "")
    table.add_row("Max Papers", str(config.max_papers), "")
    table.add_row("Relevance Threshold", str(config.relevance_threshold), "")
    table.add_row("Cache Enabled", str(config.cache_enabled), "")

    console.print(table)

    if config.validate_keys():
        console.print("\n[bold green]✓ Configuration is valid[/bold green]")
    else:
        console.print("\n[bold red]✗ Configuration incomplete[/bold red]")
        console.print("Please set required API keys in .env file")


@cli.command()
def version():
    """Show version information."""
    from .. import __version__

    console.print(f"\n[bold cyan]Research Graph Explorer[/bold cyan] version [green]{__version__}[/green]\n")


if __name__ == "__main__":
    cli()
