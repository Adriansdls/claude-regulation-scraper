"""Enhanced interactive chat interface for the Network Science Agent.

Beautiful terminal UI with:
- Multi-line input
- Smart autocomplete
- Token/cost tracking
- Terminal plots
- Syntax highlighting
- Status bar
- And more!
"""

import asyncio
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from ..agent import NetworkScienceAgent
from .ui import (
    TerminalPlotter,
    QueryCompleter,
    StatusBar,
    TokenTracker,
    CodeHighlighter,
    async_multiline_prompt,
    SessionInfo,
)


console = Console()
plotter = TerminalPlotter(width=80, height=20)
highlighter = CodeHighlighter(console=console)


def print_welcome():
    """Print enhanced welcome message."""
    welcome = """
# 🧠 Network Science Research Assistant [Enhanced]

Ask me questions about your research graph in **natural language**:

## What I Can Do
• **Find literature gaps** - Discover underexplored research areas
• **Detect echo chambers** - Identify citation rings and insular communities
• **Analyze influence** - Find the most important papers and concepts
• **Explore connections** - Trace how ideas are connected
• **Study communities** - Understand research field structure
• **Author networks** - Analyze collaboration patterns
• **Custom queries** - Write NetworkX code dynamically!

## New Features ✨
• **Multi-line mode** - End query with `\\` for complex multi-line questions
• **Smart autocomplete** - Press Tab for suggestions
• **Terminal plots** - Visual charts right in your terminal
• **Token tracking** - Real-time cost & usage monitoring
• **Syntax highlighting** - Beautiful code display

## Commands
- `help` - Show example queries
- `stats` - Show graph statistics with plots
- `memory` - See saved insights
- `usage` - Show token usage & costs
- `clear` - Clear conversation history
- `export` - Export session (coming soon)
- `exit` or `quit` - Exit

## Tips
- Use **Tab** for autocomplete
- End line with `\\` for multi-line input
- I'll show my thinking and ask for clarification when needed

Let's explore your research graph! 🚀
"""

    console.print(Panel.fit(
        Markdown(welcome),
        border_style="cyan",
        title="[bold cyan]Welcome[/bold cyan]",
        padding=(1, 2)
    ))


def print_help():
    """Print help with example queries and templates."""
    help_text = """
# Example Queries

## Finding Gaps
- "find gaps in the literature"
- "what concepts are underexplored in my domain?"
- "show me important but isolated concepts"
- "are there any disconnected research communities?"

## Influence & Importance
- "who are the most influential authors?"
- "what are the most important papers by pagerank?"
- "show me bridge papers connecting different areas"
- "find papers with high betweenness centrality"

## Echo Chambers
- "are there citation rings in my graph?"
- "find clusters with high self-citation"
- "detect echo chambers"
- "show me insular research communities"

## Research Communities
- "find research communities in my graph"
- "how is the field organized?"
- "show me the structure of research clusters"
- "which papers belong to which communities?"

## Trends & Patterns
- "what topics are emerging?"
- "show me research trends over time"
- "find declining research areas"
- "how has the field evolved?"

## Connections
- "how is paper A connected to paper B?"
- "find all paths between two concepts"
- "show me the knowledge flow between works"

## Custom Analysis (Dynamic Code!)
- "count papers by year and plot it"
- "find papers citing both BERT and GPT"
- "calculate clustering coefficient"
- "show me co-authorship patterns"

## Multi-line Example
```
find papers that: \\
  - are about transformers
  - published after 2020
  - have high betweenness
  and show me a plot
```

**Tip:** Press Tab for autocomplete suggestions!
"""

    console.print(Panel(
        Markdown(help_text),
        border_style="blue",
        title="[bold blue]Help & Examples[/bold blue]",
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

    # Show recent 15
    for insight in insights[-15:]:
        timestamp = insight["timestamp"][:10]  # Just date
        tags_str = ", ".join(insight["tags"]) if insight["tags"] else "no tags"

        console.print(f"[dim]{timestamp}[/dim] | [cyan]{tags_str}[/cyan]")
        console.print(f"  {insight['insight'][:150]}...")
        console.print()


def show_usage_stats(tracker: TokenTracker):
    """Show detailed usage statistics."""
    console.print("\n")

    # Session summary table
    summary = tracker.session.get_summary()

    table = Table(title="Session Usage Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Total Queries", str(summary["total_queries"]))
    table.add_row("Total Tokens", f"{summary['total_tokens']:,}")
    table.add_row("  Input", f"{summary['input_tokens']:,}")
    table.add_row("  Output", f"{summary['output_tokens']:,}")
    table.add_row("  Cache Read", f"{summary['cache_read_tokens']:,}")
    table.add_row("  Cache Creation", f"{summary['cache_creation_tokens']:,}")
    table.add_row("Total Cost", f"${summary['total_cost']:.4f}", style="green")
    table.add_row("Avg Query Time", f"{summary['average_query_time']:.2f}s")
    table.add_row("Session Duration", f"{summary['session_duration'] / 60:.1f} min")
    table.add_row("Model", summary["model"])

    console.print(table)
    console.print()

    # Plot token usage over queries if we have enough data
    if len(tracker.session.queries) >= 3:
        query_nums = list(range(1, len(tracker.session.queries) + 1))
        token_counts = [q.total_tokens for q in tracker.session.queries]

        plot = plotter.plot_line(
            x=query_nums,
            y=token_counts,
            title="Token Usage Per Query",
            xlabel="Query #",
            ylabel="Tokens",
            color="green"
        )
        console.print(plot)


async def chat_loop(knowledge_graph_path: str, api_key: str = None):
    """
    Enhanced chat loop with all new features.

    Args:
        knowledge_graph_path: Path to knowledge graph JSON
        api_key: Anthropic API key (optional, reads from env if not provided)
    """
    print_welcome()

    # Initialize components
    with console.status("[bold green]Loading knowledge graph & initializing agent..."):
        try:
            agent = NetworkScienceAgent(
                knowledge_graph_path=knowledge_graph_path,
                api_key=api_key
            )

            # Initialize UI components
            token_tracker = TokenTracker(model="claude-sonnet-4")
            status_bar = StatusBar(console=console, position="bottom")
            session_info = SessionInfo()

            # Update status bar with graph info
            graph_name = Path(knowledge_graph_path).stem
            stats = agent.kg.get_statistics()
            papers = stats.get("papers", {})
            entities = stats.get("entities", {})

            status_bar.update(
                graph_name=graph_name,
                num_papers=papers.get("total_papers", 0),
                num_entities=entities.get("total_entities", 0),
                model_name="claude-sonnet-4"
            )

            console.print("[green]✓[/green] Agent ready!\n")

        except Exception as e:
            console.print(f"[red]Error loading knowledge graph: {e}[/red]")
            return

    # Set up prompt session with history and autocomplete
    if PROMPT_TOOLKIT_AVAILABLE:
        history_file = Path.home() / ".rge" / "chat_history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history = FileHistory(str(history_file))

        # Create smart completer with graph data
        completer = QueryCompleter(
            knowledge_graph=agent.kg,
            enable_templates=True,
            enable_fuzzy=True
        )
    else:
        history = None
        completer = None

    # Print initial status
    console.print(f"[dim]{status_bar.render()}[/dim]\n")

    # Main loop
    while True:
        try:
            # Get user input (with multi-line support)
            if PROMPT_TOOLKIT_AVAILABLE:
                user_input = await async_multiline_prompt(
                    message="You: ",
                    completer=completer,
                    multiline_trigger="\\",
                    history=history
                )
            else:
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if not user_input.strip():
                continue

            user_input = user_input.strip()

            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                # Show session summary
                console.print("\n[bold cyan]Session Summary[/bold cyan]")
                show_usage_stats(token_tracker)
                console.print("\n[cyan]Goodbye! Happy researching! 🚀[/cyan]\n")
                break

            elif user_input.lower() == 'help':
                print_help()
                continue

            elif user_input.lower() == 'stats':
                # Enhanced stats with plots
                with console.status("[bold green]Analyzing graph..."):
                    stats = agent.kg.get_statistics()

                # Display stats table
                table = Table(title="Knowledge Graph Statistics", show_header=True)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green", justify="right")

                papers_data = stats.get("papers", {})
                entities_data = stats.get("entities", {})
                relationships_data = stats.get("relationships", {})

                table.add_row("Papers", str(papers_data.get("total_papers", 0)))
                table.add_row("Entities", str(entities_data.get("total_entities", 0)))
                table.add_row("Relationships", str(relationships_data.get("total_relationships", 0)))
                table.add_row("Citations", str(papers_data.get("total_citations", 0)))

                console.print("\n")
                console.print(table)

                # Plot degree distribution if available
                if hasattr(agent.kg, 'paper_graph'):
                    degrees = [d for _, d in agent.kg.paper_graph.degree()]
                    if degrees:
                        plot = plotter.plot_degree_distribution(degrees)
                        console.print("\n")
                        console.print(plot)

                console.print()
                continue

            elif user_input.lower() == 'memory':
                print_memory_insights(agent)
                continue

            elif user_input.lower() == 'usage':
                show_usage_stats(token_tracker)
                continue

            elif user_input.lower() == 'clear':
                agent.reset()
                console.print("[yellow]Conversation history cleared.[/yellow]\n")
                continue

            # Process query with agent
            token_tracker.start_query()
            session_info.record_query()

            console.print("\n[bold green]Agent:[/bold green] ", end="")

            # Track tool usage
            tools_used_in_query = 0
            showing_tools = False

            # Stream agent responses
            async for message in agent.query(user_input):
                if message["type"] == "text":
                    # Agent text output with syntax highlighting
                    text = message["text"]

                    # Check for code blocks and highlight
                    if "```" in text:
                        formatted = highlighter.detect_and_highlight(text)
                        console.print(formatted, end="")
                    else:
                        console.print(text, end="")

                elif message["type"] == "tool_use":
                    # Tool being used
                    if not showing_tools:
                        console.print()  # New line
                        showing_tools = True

                    tool_name = message["tool_name"]
                    tools_used_in_query += 1
                    session_info.record_tool_use(tool_name)

                    console.print(f"\n[dim]→ Using {tool_name}...[/dim]", end="")

                elif message["type"] == "tool_result":
                    # Tool result
                    result = message["result"]

                    # Show interpretation if available
                    if isinstance(result, dict) and "interpretation" in result:
                        console.print(f" [dim green]✓[/dim green]")

                    # Show plots if available
                    if isinstance(result, dict) and "display" in result:
                        console.print(result["display"])

                    # Enhanced visualization for certain result types
                    if isinstance(result, dict):
                        # Community results - add plot
                        if "communities" in result and "modularity" in result:
                            communities = result.get("communities", {})
                            if communities:
                                plot = plotter.plot_community_sizes(communities, top_n=15)
                                console.print("\n")
                                console.print(plot)

                        # Centrality results - add distribution plot
                        elif "centrality_scores" in result:
                            scores = result.get("centrality_scores", {})
                            metric = result.get("metric", "centrality")
                            if scores:
                                plot = plotter.plot_centrality_distribution(scores, metric=metric)
                                console.print("\n")
                                console.print(plot)

            # End with newline
            console.print("\n")

            # Update token tracking (estimate for now)
            # In real implementation, would get actual token counts from API response
            input_tokens = token_tracker.estimate_tokens(user_input + str(agent.messages))
            output_tokens = token_tracker.estimate_tokens("estimated")  # Would get from API

            metrics = token_tracker.end_query(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tool_calls=tools_used_in_query
            )

            # Update status bar
            status_bar.update(
                query_count=session_info.queries_executed,
                session_cost=token_tracker.session.total_cost
            )

            # Show compact status line
            console.print(f"[dim]{status_bar.render()} | {metrics.execution_time:.2f}s[/dim]\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]\n")
            session_info.record_error()
            continue

        except EOFError:
            break

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")
            session_info.record_error()

            import traceback
            if "--debug" in sys.argv:
                traceback.print_exc()


def main():
    """Entry point for enhanced chat command."""
    import sys

    if len(sys.argv) < 2:
        console.print("[red]Usage: rge chat <knowledge_graph.json>[/red]")
        console.print("\nExample:")
        console.print("  rge chat knowledge_graph.json")
        console.print("\nOptions:")
        console.print("  --debug    Show debug information")
        sys.exit(1)

    knowledge_graph_path = sys.argv[1]

    # Check if file exists
    if not Path(knowledge_graph_path).exists():
        console.print(f"[red]Error: File not found: {knowledge_graph_path}[/red]")
        sys.exit(1)

    # Run enhanced chat loop
    try:
        asyncio.run(chat_loop(knowledge_graph_path))
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")


if __name__ == "__main__":
    main()
