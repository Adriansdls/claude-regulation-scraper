"""Interactive chat interface for the Network Science Agent.

Beautiful terminal UI inspired by Claude Code's elegance.
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Prompt
from rich.table import Table

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from ..agent import NetworkScienceAgent


console = Console()


def print_welcome():
    """Print welcome message."""
    welcome = """
# 🧠 Network Science Research Assistant

Ask me questions about your research graph:
• **Find literature gaps** - Discover underexplored research areas
• **Detect echo chambers** - Identify citation rings and insular communities
• **Analyze influence** - Find the most important papers and concepts
• **Explore connections** - Trace how ideas are connected
• **Study communities** - Understand research field structure
• **Author networks** - Analyze collaboration patterns

**Commands:**
- `help` - Show example queries
- `stats` - Show graph statistics
- `memory` - See saved insights
- `clear` - Clear conversation history
- `exit` or `quit` - Exit

I'll show my thinking, use tools transparently, and ask for clarification when needed.

Let's explore your research graph!
"""

    console.print(Panel.fit(
        Markdown(welcome),
        border_style="cyan",
        title="[bold cyan]Welcome[/bold cyan]",
        padding=(1, 2)
    ))


def print_help():
    """Print help with example queries."""
    help_text = """
# Example Queries

## Finding Gaps
- "Find gaps in the graph neural networks literature"
- "What concepts are underexplored in my domain?"
- "Show me important but isolated concepts"
- "Are there any disconnected research communities?"

## Influence & Importance
- "Who are the most influential authors?"
- "What are the most important papers by PageRank?"
- "Show me bridge papers connecting different areas"
- "Find papers with high betweenness centrality"

## Echo Chambers
- "Are there citation rings in my graph?"
- "Find clusters with high self-citation"
- "Detect echo chambers"
- "Show me insular research communities"

## Research Communities
- "Find research communities in my graph"
- "How is the field organized?"
- "Show me the structure of research clusters"
- "Which papers belong to which communities?"

## Trends & Patterns
- "What topics are emerging?"
- "Show me research trends over time"
- "Find declining research areas"
- "How has the field evolved?"

## Connections
- "How is paper A connected to paper B?"
- "Find all paths between two concepts"
- "Show me the knowledge flow between works"

## Custom Analysis
- "Count papers by year"
- "Find papers citing both BERT and GPT but not transformers"
- "Calculate clustering coefficient"
- "Show me co-authorship patterns"

For custom analyses, I can write NetworkX code dynamically!
"""

    console.print(Panel(
        Markdown(help_text),
        border_style="blue",
        title="[bold blue]Help[/bold blue]",
        expand=False
    ))


def print_memory_insights(agent: NetworkScienceAgent):
    """Show saved insights from memory."""
    from ..agent.tools.memory_tools import MemoryStore

    memory = MemoryStore()
    insights = memory.get_all()

    if not insights:
        console.print("[yellow]No insights saved yet.[/yellow]\n")
        return

    console.print(f"\n[bold cyan]💾 Saved Insights ({len(insights)} total)[/bold cyan]\n")

    # Show recent 10
    for insight in insights[-10:]:
        timestamp = insight["timestamp"][:10]  # Just date
        tags_str = ", ".join(insight["tags"]) if insight["tags"] else "no tags"

        console.print(f"[dim]{timestamp}[/dim] | [cyan]{tags_str}[/cyan]")
        console.print(f"  {insight['insight'][:100]}...")
        console.print()


async def chat_loop(knowledge_graph_path: str, api_key: str = None):
    """
    Main chat loop.

    Args:
        knowledge_graph_path: Path to knowledge graph JSON
        api_key: Anthropic API key (optional, reads from env if not provided)
    """
    print_welcome()

    # Initialize agent
    with console.status("[bold green]Loading knowledge graph..."):
        try:
            agent = NetworkScienceAgent(
                knowledge_graph_path=knowledge_graph_path,
                api_key=api_key
            )
            console.print("[green]✓[/green] Agent ready!\n")
        except Exception as e:
            console.print(f"[red]Error loading knowledge graph: {e}[/red]")
            return

    # Set up prompt session with history
    if PROMPT_TOOLKIT_AVAILABLE:
        history_file = Path.home() / ".rge" / "chat_history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        session = PromptSession(history=FileHistory(str(history_file)))
    else:
        session = None

    # Main loop
    while True:
        try:
            # Get user input
            if session:
                user_input = await session.prompt_async("You: ", multiline=False)
            else:
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if not user_input.strip():
                continue

            user_input = user_input.strip()

            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("\n[cyan]Goodbye! Happy researching! 🚀[/cyan]\n")
                break

            elif user_input.lower() == 'help':
                print_help()
                continue

            elif user_input.lower() == 'stats':
                # Quick stats
                with console.status("[bold green]Getting graph statistics..."):
                    stats = agent.kg.get_statistics()

                # Display stats
                table = Table(title="Knowledge Graph Statistics", show_header=True)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green", justify="right")

                papers = stats.get("papers", {})
                entities = stats.get("entities", {})
                relationships = stats.get("relationships", {})

                table.add_row("Papers", str(papers.get("total_papers", 0)))
                table.add_row("Entities", str(entities.get("total_entities", 0)))
                table.add_row("Relationships", str(relationships.get("total_relationships", 0)))
                table.add_row("Citations", str(papers.get("total_citations", 0)))

                console.print("\n")
                console.print(table)
                console.print()
                continue

            elif user_input.lower() == 'memory':
                print_memory_insights(agent)
                continue

            elif user_input.lower() == 'clear':
                agent.reset()
                console.print("[yellow]Conversation history cleared.[/yellow]\n")
                continue

            # Process query with agent
            console.print("\n[bold green]Agent:[/bold green] ", end="")

            # Track if we're showing tool use
            showing_tools = False

            # Stream agent responses
            async for message in agent.query(user_input):
                if message["type"] == "text":
                    # Agent text output
                    console.print(message["text"], end="")

                elif message["type"] == "tool_use":
                    # Tool being used
                    if not showing_tools:
                        console.print()  # New line
                        showing_tools = True

                    tool_name = message["tool_name"]
                    console.print(f"\n[dim]→ Using {tool_name}...[/dim]", end="")

                elif message["type"] == "tool_result":
                    # Tool result (don't show raw - agent will synthesize)
                    result = message["result"]

                    # Show interpretation if available
                    if isinstance(result, dict) and "interpretation" in result:
                        console.print(f" [dim]{result['interpretation']}[/dim]")

                    # Show display if available (for visualizations)
                    if isinstance(result, dict) and "display" in result:
                        console.print(result["display"])

            # End with newline
            console.print("\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]\n")
            continue

        except EOFError:
            break

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")
            import traceback
            if "--debug" in sys.argv:
                traceback.print_exc()


def main():
    """Entry point for chat command."""
    import sys

    if len(sys.argv) < 2:
        console.print("[red]Usage: rge chat <knowledge_graph.json>[/red]")
        console.print("\nExample:")
        console.print("  rge chat knowledge_graph.json")
        sys.exit(1)

    knowledge_graph_path = sys.argv[1]

    # Check if file exists
    if not Path(knowledge_graph_path).exists():
        console.print(f"[red]Error: File not found: {knowledge_graph_path}[/red]")
        sys.exit(1)

    # Run chat loop
    try:
        asyncio.run(chat_loop(knowledge_graph_path))
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")


if __name__ == "__main__":
    main()
