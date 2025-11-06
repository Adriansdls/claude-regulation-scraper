"""Token usage and cost tracking.

Track API usage, costs, and performance metrics for transparency.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


# Pricing per 1M tokens (as of 2024-11)
# Update these as pricing changes
PRICING = {
    "claude-opus-4": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-sonnet-3.5": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-3.5": {
        "input": 0.80,
        "output": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
}


@dataclass
class QueryMetrics:
    """Metrics for a single query."""

    query_id: int
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    tool_calls: int = 0
    execution_time: float = 0.0  # seconds
    model: str = "claude-sonnet-4"

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return (
            self.input_tokens +
            self.output_tokens +
            self.cache_creation_tokens +
            self.cache_read_tokens
        )

    @property
    def cost(self) -> float:
        """Estimated cost in USD."""
        if self.model not in PRICING:
            # Default to sonnet pricing
            pricing = PRICING["claude-sonnet-4"]
        else:
            pricing = PRICING[self.model]

        cost = (
            (self.input_tokens / 1_000_000) * pricing["input"] +
            (self.output_tokens / 1_000_000) * pricing["output"] +
            (self.cache_creation_tokens / 1_000_000) * pricing["cache_write"] +
            (self.cache_read_tokens / 1_000_000) * pricing["cache_read"]
        )

        return cost


@dataclass
class SessionMetrics:
    """Metrics for entire session."""

    start_time: datetime = field(default_factory=datetime.now)
    queries: list[QueryMetrics] = field(default_factory=list)
    model: str = "claude-sonnet-4"

    @property
    def total_queries(self) -> int:
        """Total number of queries."""
        return len(self.queries)

    @property
    def total_tokens(self) -> int:
        """Total tokens across all queries."""
        return sum(q.total_tokens for q in self.queries)

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens."""
        return sum(q.input_tokens for q in self.queries)

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens."""
        return sum(q.output_tokens for q in self.queries)

    @property
    def total_cache_read_tokens(self) -> int:
        """Total cache read tokens."""
        return sum(q.cache_read_tokens for q in self.queries)

    @property
    def total_cache_creation_tokens(self) -> int:
        """Total cache creation tokens."""
        return sum(q.cache_creation_tokens for q in self.queries)

    @property
    def total_cost(self) -> float:
        """Total estimated cost."""
        return sum(q.cost for q in self.queries)

    @property
    def average_query_time(self) -> float:
        """Average query execution time."""
        if not self.queries:
            return 0.0
        return sum(q.execution_time for q in self.queries) / len(self.queries)

    @property
    def session_duration(self) -> float:
        """Session duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def add_query(self, metrics: QueryMetrics):
        """Add query metrics to session."""
        self.queries.append(metrics)

    def get_summary(self) -> Dict:
        """Get session summary."""
        return {
            "total_queries": self.total_queries,
            "total_tokens": self.total_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cache_read_tokens": self.total_cache_read_tokens,
            "cache_creation_tokens": self.total_cache_creation_tokens,
            "total_cost": self.total_cost,
            "average_query_time": self.average_query_time,
            "session_duration": self.session_duration,
            "model": self.model,
        }


class TokenTracker:
    """Track token usage and costs throughout session."""

    def __init__(self, model: str = "claude-sonnet-4"):
        """
        Initialize token tracker.

        Args:
            model: Model name for pricing
        """
        self.session = SessionMetrics(model=model)
        self.current_query_start: Optional[float] = None
        self.encoding = None

        # Try to load tokenizer
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base (GPT-4 tokenizer as approximation)
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

    def start_query(self):
        """Mark start of query."""
        self.current_query_start = time.time()

    def end_query(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        tool_calls: int = 0
    ) -> QueryMetrics:
        """
        Mark end of query and record metrics.

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
            tool_calls: Number of tool calls

        Returns:
            QueryMetrics for this query
        """
        execution_time = 0.0
        if self.current_query_start:
            execution_time = time.time() - self.current_query_start

        metrics = QueryMetrics(
            query_id=self.session.total_queries + 1,
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            tool_calls=tool_calls,
            execution_time=execution_time,
            model=self.session.model
        )

        self.session.add_query(metrics)
        self.current_query_start = None

        return metrics

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough approximation: 4 chars per token
            return len(text) // 4

    def get_status_line(self) -> str:
        """
        Get one-line status for display.

        Returns:
            Status string
        """
        summary = self.session.get_summary()

        if summary["total_queries"] == 0:
            return f"Model: {summary['model']} | Session: $0.00 | 0 queries"

        # Format tokens with K suffix
        total_k = summary["total_tokens"] / 1000

        return (
            f"Model: {summary['model']} | "
            f"Session: ${summary['total_cost']:.3f} | "
            f"{total_k:.1f}K tokens | "
            f"{summary['total_queries']} queries"
        )

    def get_detailed_status(self) -> str:
        """
        Get detailed status display.

        Returns:
            Multi-line status string
        """
        summary = self.session.get_summary()

        lines = [
            "Session Statistics:",
            f"  Queries: {summary['total_queries']}",
            f"  Total Tokens: {summary['total_tokens']:,}",
            f"    Input: {summary['input_tokens']:,}",
            f"    Output: {summary['output_tokens']:,}",
            f"    Cache Read: {summary['cache_read_tokens']:,}",
            f"    Cache Creation: {summary['cache_creation_tokens']:,}",
            f"  Total Cost: ${summary['total_cost']:.4f}",
            f"  Avg Query Time: {summary['average_query_time']:.2f}s",
            f"  Session Duration: {summary['session_duration'] / 60:.1f} min",
            f"  Model: {summary['model']}",
        ]

        return "\n".join(lines)

    def get_last_query_summary(self) -> str:
        """Get summary of last query."""
        if not self.session.queries:
            return "No queries yet"

        last = self.session.queries[-1]

        return (
            f"Last query: {last.total_tokens:,} tokens | "
            f"${last.cost:.4f} | "
            f"{last.execution_time:.2f}s | "
            f"{last.tool_calls} tools"
        )


def format_token_count(count: int) -> str:
    """
    Format token count with K/M suffix.

    Args:
        count: Token count

    Returns:
        Formatted string
    """
    if count < 1000:
        return str(count)
    elif count < 1_000_000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1_000_000:.1f}M"


def format_cost(cost: float) -> str:
    """
    Format cost in USD.

    Args:
        cost: Cost in dollars

    Returns:
        Formatted string
    """
    if cost < 0.01:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"
