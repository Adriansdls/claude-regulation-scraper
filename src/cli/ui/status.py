"""Status bar for context awareness.

Display persistent status information at top or bottom of terminal.
"""

from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from datetime import datetime


class StatusBar:
    """Persistent status bar showing session context."""

    def __init__(
        self,
        console: Optional[Console] = None,
        position: str = "bottom"
    ):
        """
        Initialize status bar.

        Args:
            console: Rich console instance
            position: "top" or "bottom"
        """
        self.console = console or Console()
        self.position = position
        self.visible = True

        # Status data
        self.graph_name: Optional[str] = None
        self.num_papers: int = 0
        self.num_entities: int = 0
        self.query_count: int = 0
        self.session_cost: float = 0.0
        self.model_name: str = "claude-sonnet-4"
        self.memory_count: int = 0

    def update(self, **kwargs):
        """
        Update status bar data.

        Args:
            **kwargs: Status fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def render(self) -> str:
        """
        Render status bar as string.

        Returns:
            Status bar content
        """
        parts = []

        # Graph info
        if self.graph_name:
            parts.append(f"📊 {self.graph_name}")
        if self.num_papers > 0:
            parts.append(f"{self.num_papers} papers")

        # Query count
        if self.query_count > 0:
            parts.append(f"Q#{self.query_count}")

        # Cost
        if self.session_cost > 0:
            parts.append(f"${self.session_cost:.3f}")

        # Memory
        if self.memory_count > 0:
            parts.append(f"💾 {self.memory_count}")

        # Model
        parts.append(f"🤖 {self.model_name}")

        # Join with separator
        return " │ ".join(parts)

    def render_detailed(self) -> Table:
        """
        Render detailed status as table.

        Returns:
            Rich table with status
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        if self.graph_name:
            table.add_row("Graph", self.graph_name)

        if self.num_papers > 0:
            table.add_row("Papers", f"{self.num_papers:,}")

        if self.num_entities > 0:
            table.add_row("Entities", f"{self.num_entities:,}")

        if self.query_count > 0:
            table.add_row("Queries", str(self.query_count))

        if self.session_cost > 0:
            table.add_row("Session Cost", f"${self.session_cost:.4f}")

        if self.memory_count > 0:
            table.add_row("Saved Insights", str(self.memory_count))

        table.add_row("Model", self.model_name)

        return table

    def print(self):
        """Print status bar."""
        if not self.visible:
            return

        status_line = self.render()

        # Create panel
        panel = Panel(
            status_line,
            border_style="dim",
            padding=(0, 1),
            expand=True
        )

        self.console.print(panel)

    def get_compact_line(self) -> str:
        """
        Get compact one-line status.

        Returns:
            Single line status string
        """
        return self.render()


class ContextDisplay:
    """Display current context and recent actions."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize context display.

        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.current_tool: Optional[str] = None
        self.recent_actions: list[str] = []
        self.max_actions = 5

    def set_current_tool(self, tool_name: str):
        """Set currently executing tool."""
        self.current_tool = tool_name

    def clear_current_tool(self):
        """Clear current tool."""
        self.current_tool = None

    def add_action(self, action: str):
        """
        Add action to recent history.

        Args:
            action: Action description
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_actions.insert(0, f"[{timestamp}] {action}")
        self.recent_actions = self.recent_actions[:self.max_actions]

    def get_current_status(self) -> str:
        """Get current status line."""
        if self.current_tool:
            return f"⚙️  Using {self.current_tool}..."
        elif self.recent_actions:
            return f"✓ {self.recent_actions[0]}"
        else:
            return "Ready"

    def render_recent_actions(self) -> Table:
        """Render recent actions table."""
        table = Table(title="Recent Actions", show_header=False, box=None)
        table.add_column("Action", style="dim")

        for action in self.recent_actions:
            table.add_row(action)

        return table


class SessionInfo:
    """Track and display session information."""

    def __init__(self):
        """Initialize session info."""
        self.start_time = datetime.now()
        self.queries_executed = 0
        self.tools_used: Dict[str, int] = {}
        self.insights_saved = 0
        self.errors_encountered = 0

    def record_query(self):
        """Record query execution."""
        self.queries_executed += 1

    def record_tool_use(self, tool_name: str):
        """Record tool usage."""
        self.tools_used[tool_name] = self.tools_used.get(tool_name, 0) + 1

    def record_insight(self):
        """Record insight saved."""
        self.insights_saved += 1

    def record_error(self):
        """Record error."""
        self.errors_encountered += 1

    def get_duration(self) -> float:
        """Get session duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return {
            "start_time": self.start_time,
            "duration_seconds": self.get_duration(),
            "queries_executed": self.queries_executed,
            "tools_used": self.tools_used,
            "insights_saved": self.insights_saved,
            "errors_encountered": self.errors_encountered,
            "most_used_tool": max(self.tools_used.items(), key=lambda x: x[1])[0] if self.tools_used else None,
        }

    def render_summary(self) -> Table:
        """Render session summary table."""
        summary = self.get_summary()

        table = Table(title="Session Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        # Duration
        duration_min = summary["duration_seconds"] / 60
        table.add_row("Duration", f"{duration_min:.1f} min")

        # Queries
        table.add_row("Queries", str(summary["queries_executed"]))

        # Tools
        table.add_row("Tools Used", str(len(summary["tools_used"])))

        if summary["most_used_tool"]:
            table.add_row("Most Used Tool", summary["most_used_tool"])

        # Insights
        if summary["insights_saved"] > 0:
            table.add_row("Insights Saved", str(summary["insights_saved"]))

        # Errors
        if summary["errors_encountered"] > 0:
            table.add_row("Errors", str(summary["errors_encountered"]), style="red")

        return table
