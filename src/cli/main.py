"""Main CLI for Research Graph Explorer."""

import asyncio
import json
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.panel import Panel
from rich.markdown import Markdown

from ..discovery.seed_generator import SeedGenerator
from ..discovery.frontier_explorer import FrontierExplorer
from ..models.paper import Paper
from ..infrastructure.config import get_config


console = Console()


def print_welcome_banner():
    """Print the amazing welcome banner - like starting a video game!"""
    banner = """
# 🔬 Research Graph Explorer (RGE)

**AI-Powered Paper Discovery & Network Science Analysis**

---

Welcome to your research command center! RGE helps you explore academic literature
like never before - discover papers, extract knowledge, and chat with your research
using cutting-edge AI agents.

## 🚀 Quick Start Workflows

### 1️⃣  Discover New Research
```bash
rge discover "What are the latest advances in transformers?"
```
Intelligently searches and scores papers relevant to your question

### 2️⃣  Extract Knowledge
```bash
rge extract papers.json --ontology config/ontologies/ml_research.yaml
```
Builds a knowledge graph from your papers using custom ontologies

### 3️⃣  Chat with Your Research
```bash
rge chat                     # Auto-detects knowledge graph
rge chat --list              # List available graphs
```
Ask natural language questions, find gaps, detect echo chambers!

## 📋 All Commands

- `rge discover <question>` - Discover relevant papers
- `rge extract <file>` - Extract knowledge graph
- `rge chat [graph]` - Interactive research assistant
- `rge config-check` - Verify API keys & settings
- `rge version` - Show version info

## 💡 First Time Here?

1. Check your config: `rge config-check`
2. Discover some papers: `rge discover "your research question"`
3. Extract knowledge: `rge extract papers.json --ontology <ontology.yaml>`
4. Start chatting: `rge chat`

## 🎯 Need Help?

- Full docs: [Coming soon]
- Examples: `rge <command> --help`
- GitHub: [Your repo URL]

**Ready to explore? Run any command above to get started! 🎉**
"""

    console.print(Panel.fit(
        Markdown(banner),
        border_style="cyan",
        title="[bold cyan]✨ Welcome to RGE ✨[/bold cyan]",
        subtitle="[dim]Run 'rge --help' for more options[/dim]",
        padding=(1, 2)
    ))


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Research Graph Explorer - AI-powered paper discovery and analysis."""
    # Show welcome banner if no command given
    if ctx.invoked_subcommand is None:
        print_welcome_banner()
        console.print()  # Extra spacing


@cli.command()
@click.argument("knowledge_graph_path", required=False)
@click.option("--api-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
@click.option("--list", is_flag=True, help="List available knowledge graphs")
def chat(knowledge_graph_path: str, api_key: str, list: bool):
    """
    Interactive chat with the Network Science Agent.

    Ask questions about your research graph in natural language!

    Examples:
        rge chat                          # Auto-detect knowledge graph
        rge chat knowledge_graph.json     # Use specific graph
        rge chat --list                   # List available graphs

    The agent can:
    - Find literature gaps
    - Detect echo chambers
    - Analyze influence and importance
    - Study research communities
    - Trace connections between papers
    - Write custom NetworkX code for novel analyses
    """
    import glob

    # List available graphs if requested
    if list:
        console.print("\n[bold cyan]Available Knowledge Graphs:[/bold cyan]\n")
        graphs = glob.glob("**/*.json", recursive=True)
        kg_files = [g for g in graphs if "knowledge" in g.lower() or "kg" in g.lower()]

        if not kg_files:
            console.print("[yellow]No knowledge graph files found.[/yellow]")
            console.print("\nTip: Run 'rge discover' then 'rge extract' to create one!\n")
        else:
            for i, kg in enumerate(kg_files, 1):
                size = Path(kg).stat().st_size / 1024  # KB
                console.print(f"{i}. [cyan]{kg}[/cyan] [dim]({size:.1f} KB)[/dim]")
            console.print()
        return

    # Auto-detect knowledge graph if not provided
    if not knowledge_graph_path:
        # Look for common patterns
        candidates = []
        for pattern in ["knowledge_graph.json", "kg.json", "*knowledge*.json", "*kg*.json"]:
            candidates.extend(glob.glob(pattern))
            candidates.extend(glob.glob(f"**/{pattern}", recursive=True))

        # Remove duplicates and sort by modification time
        candidates = list(set(candidates))
        if candidates:
            candidates.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)

        if not candidates:
            console.print("\n[bold red]No knowledge graph found![/bold red]\n")
            console.print("[yellow]You need a knowledge graph to chat with.[/yellow]")
            console.print("\nOptions:")
            console.print("  1. Create one:")
            console.print("     [cyan]rge discover 'your research question'[/cyan]")
            console.print("     [cyan]rge extract papers.json --ontology config/ontologies/ml_research.yaml[/cyan]")
            console.print("\n  2. Specify a path:")
            console.print("     [cyan]rge chat /path/to/knowledge_graph.json[/cyan]")
            console.print("\n  3. List available graphs:")
            console.print("     [cyan]rge chat --list[/cyan]\n")
            return

        if len(candidates) == 1:
            knowledge_graph_path = candidates[0]
            console.print(f"\n[green]✓[/green] Auto-detected knowledge graph: [cyan]{knowledge_graph_path}[/cyan]\n")
        else:
            # Multiple found - let user choose
            console.print(f"\n[bold cyan]Found {len(candidates)} knowledge graphs:[/bold cyan]\n")
            for i, kg in enumerate(candidates[:10], 1):  # Show top 10
                size = Path(kg).stat().st_size / 1024
                mtime = Path(kg).stat().st_mtime
                from datetime import datetime
                date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                console.print(f"{i}. [cyan]{kg}[/cyan]")
                console.print(f"   [dim]{size:.1f} KB | Modified: {date}[/dim]")

            console.print("\nUsing most recent: [cyan]" + candidates[0] + "[/cyan]")
            console.print("[dim]Tip: Specify a different one with 'rge chat <path>'[/dim]\n")
            knowledge_graph_path = candidates[0]

    # Validate path exists
    if not Path(knowledge_graph_path).exists():
        console.print(f"\n[bold red]Error:[/bold red] File not found: {knowledge_graph_path}\n")
        console.print("Run [cyan]rge chat --list[/cyan] to see available graphs.\n")
        return

    from .chat import chat_loop
    asyncio.run(chat_loop(knowledge_graph_path, api_key))


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
@click.argument("discovery_file")
@click.option("--ontology", required=True, help="Path to ontology YAML file")
@click.option("--output", default=None, help="Output file for knowledge graph (JSON)")
@click.option("--max-papers", default=None, type=int, help="Maximum papers to extract from")
@click.option("--download-pdfs/--no-download-pdfs", default=True, help="Download PDFs first")
def extract(discovery_file: str, ontology: str, output: str, max_papers: int, download_pdfs: bool):
    """Extract knowledge from discovered papers using an ontology.

    Example:
        rgx extract papers.json --ontology config/ontologies/ml_research.yaml --output kg.json
    """
    asyncio.run(_extract(discovery_file, ontology, output, max_papers, download_pdfs))


async def _extract(
    discovery_file: str, ontology_path: str, output: str, max_papers: int, download_pdfs: bool
):
    """Internal extract function."""
    from pathlib import Path
    import yaml
    from ..models.ontology import Ontology, EntityType, RelationType
    from ..extraction.orchestrator import ExtractionOrchestrator

    console.print("\n[bold cyan]Phase 2: Knowledge Extraction[/bold cyan]\n")

    # Load discovery results
    console.print(f"[yellow]Loading papers from:[/yellow] {discovery_file}")
    discovery_path = Path(discovery_file)
    if not discovery_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {discovery_file}")
        return

    with open(discovery_path, "r") as f:
        discovery_data = json.load(f)

    papers = [Paper(**p) for p in discovery_data.get("papers", [])]
    console.print(f"✓ Loaded {len(papers)} papers\n")

    # Load ontology
    console.print(f"[yellow]Loading ontology from:[/yellow] {ontology_path}")
    ontology_file = Path(ontology_path)
    if not ontology_file.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {ontology_path}")
        return

    with open(ontology_file, "r") as f:
        ontology_data = yaml.safe_load(f)

    # Convert to Ontology model
    ontology = Ontology(
        name=ontology_data["name"],
        description=ontology_data["description"],
        domain=ontology_data["domain"],
        version=ontology_data.get("version", "1.0.0"),
        entity_types=[EntityType(**et) for et in ontology_data.get("entity_types", [])],
        relationship_types=[
            RelationType(**rt) for rt in ontology_data.get("relationship_types", [])
        ],
    )
    console.print(f"✓ Loaded ontology: {ontology.name}")
    console.print(f"  Entity types: {[et.name for et in ontology.entity_types]}")
    console.print(f"  Relationship types: {[rt.name for rt in ontology.relationship_types]}\n")

    # Run extraction
    orchestrator = ExtractionOrchestrator(ontology)

    knowledge_graph = await orchestrator.extract_from_papers(
        papers=papers, download_pdfs=download_pdfs, max_papers=max_papers
    )

    # Save results
    if output:
        output_path = Path(output)
        orchestrator.save_graph(str(output_path))

        # Also export for Gephi
        gephi_dir = output_path.parent / f"{output_path.stem}_gephi"
        orchestrator.export_for_visualization(str(gephi_dir))

    console.print("\n[bold green]✓ Extraction complete![/bold green]")


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
