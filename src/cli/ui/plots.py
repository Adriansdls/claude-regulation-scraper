"""Terminal plotting utilities using plotext.

Beautiful visualizations right in the terminal for better data insights.
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
import io
import sys

try:
    import plotext as plt
    PLOTEXT_AVAILABLE = True
except ImportError:
    PLOTEXT_AVAILABLE = False


class TerminalPlotter:
    """Create beautiful terminal plots for research data."""

    def __init__(self, width: Optional[int] = None, height: Optional[int] = None):
        """
        Initialize plotter.

        Args:
            width: Plot width (auto-detect if None)
            height: Plot height (auto-detect if None)
        """
        self.width = width
        self.height = height

        if not PLOTEXT_AVAILABLE:
            self.enabled = False
        else:
            self.enabled = True

    def plot_histogram(
        self,
        data: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "Count",
        bins: int = 20,
        color: str = "cyan"
    ) -> str:
        """
        Create histogram plot.

        Args:
            data: Values to plot
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            bins: Number of bins
            color: Bar color

        Returns:
            Plot as string (or message if plotting disabled)
        """
        if not self.enabled or not data:
            return f"[Histogram: {title}] {len(data)} values"

        # Capture plot output
        plt.clf()

        # Set size
        if self.width and self.height:
            plt.plot_size(self.width, self.height)
        else:
            plt.plot_size(80, 20)

        # Create histogram
        plt.hist(data, bins=bins, color=color)

        # Labels
        if title:
            plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        # Build plot
        return plt.build()

    def plot_bar(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "cyan",
        horizontal: bool = False
    ) -> str:
        """
        Create bar chart.

        Args:
            labels: Bar labels
            values: Bar heights
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Bar color
            horizontal: Horizontal bars if True

        Returns:
            Plot as string
        """
        if not self.enabled or not labels:
            return f"[Bar Chart: {title}] {len(labels)} items"

        plt.clf()

        if self.width and self.height:
            plt.plot_size(self.width, self.height)
        else:
            plt.plot_size(80, 20)

        # Create bars
        if horizontal:
            plt.barh(labels, values, color=color)
        else:
            plt.bar(labels, values, color=color)

        # Labels
        if title:
            plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        return plt.build()

    def plot_line(
        self,
        x: List[Any],
        y: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "cyan",
        marker: str = "braille"
    ) -> str:
        """
        Create line plot.

        Args:
            x: X values
            y: Y values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Line color
            marker: Marker style

        Returns:
            Plot as string
        """
        if not self.enabled or not x:
            return f"[Line Plot: {title}] {len(x)} points"

        plt.clf()

        if self.width and self.height:
            plt.plot_size(self.width, self.height)
        else:
            plt.plot_size(80, 20)

        # Create line
        plt.plot(x, y, color=color, marker=marker)

        # Labels
        if title:
            plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        return plt.build()

    def plot_scatter(
        self,
        x: List[float],
        y: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "cyan",
        marker: str = "dot"
    ) -> str:
        """
        Create scatter plot.

        Args:
            x: X values
            y: Y values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Point color
            marker: Marker style

        Returns:
            Plot as string
        """
        if not self.enabled or not x:
            return f"[Scatter Plot: {title}] {len(x)} points"

        plt.clf()

        if self.width and self.height:
            plt.plot_size(self.width, self.height)
        else:
            plt.plot_size(80, 20)

        # Create scatter
        plt.scatter(x, y, color=color, marker=marker)

        # Labels
        if title:
            plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        return plt.build()

    def plot_distribution(
        self,
        values: List[float],
        title: str = "Distribution",
        show_stats: bool = True
    ) -> str:
        """
        Plot distribution with statistics.

        Args:
            values: Values to analyze
            title: Plot title
            show_stats: Show mean/median/std

        Returns:
            Plot with statistics
        """
        if not self.enabled or not values:
            return f"[Distribution: {title}] {len(values)} values"

        import statistics

        plot = self.plot_histogram(values, title=title, xlabel="Value", bins=30)

        if show_stats:
            mean = statistics.mean(values)
            median = statistics.median(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0

            stats = f"\nMean: {mean:.3f} | Median: {median:.3f} | Std: {stdev:.3f}"
            plot += stats

        return plot

    def plot_timeline(
        self,
        dates: List[Any],
        counts: List[int],
        title: str = "Timeline"
    ) -> str:
        """
        Plot timeline (e.g., papers by year).

        Args:
            dates: Date/year labels
            counts: Counts for each date
            title: Plot title

        Returns:
            Timeline plot
        """
        return self.plot_line(
            x=dates,
            y=counts,
            title=title,
            xlabel="Year",
            ylabel="Papers",
            color="green",
            marker="braille"
        )

    def plot_top_n(
        self,
        items: Dict[str, float],
        n: int = 10,
        title: str = "Top Items",
        ylabel: str = "Score"
    ) -> str:
        """
        Plot top N items from dict.

        Args:
            items: {item: score} dictionary
            n: Number of top items
            title: Plot title
            ylabel: Y-axis label

        Returns:
            Horizontal bar chart
        """
        # Sort and take top N
        sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)[:n]

        labels = [item[0][:30] for item in sorted_items]  # Truncate labels
        values = [item[1] for item in sorted_items]

        return self.plot_bar(
            labels=labels,
            values=values,
            title=title,
            ylabel=ylabel,
            color="cyan",
            horizontal=True
        )

    def plot_community_sizes(
        self,
        communities: Dict[int, List[Any]],
        top_n: int = 15
    ) -> str:
        """
        Plot community size distribution.

        Args:
            communities: {community_id: [members]}
            top_n: Show top N communities

        Returns:
            Bar chart of community sizes
        """
        sizes = {f"C{cid}": len(members) for cid, members in communities.items()}

        return self.plot_top_n(
            items=sizes,
            n=top_n,
            title=f"Community Sizes (Top {top_n})",
            ylabel="Number of Papers"
        )

    def plot_centrality_distribution(
        self,
        centrality_scores: Dict[str, float],
        metric: str = "PageRank"
    ) -> str:
        """
        Plot centrality score distribution.

        Args:
            centrality_scores: {node: score}
            metric: Centrality metric name

        Returns:
            Distribution histogram
        """
        values = list(centrality_scores.values())

        return self.plot_distribution(
            values=values,
            title=f"{metric} Distribution"
        )

    def plot_degree_distribution(
        self,
        degrees: List[int]
    ) -> str:
        """
        Plot degree distribution (log-log if needed).

        Args:
            degrees: List of node degrees

        Returns:
            Histogram of degrees
        """
        if not degrees:
            return "[No degree data]"

        # Count degree frequencies
        degree_counts = Counter(degrees)

        x = sorted(degree_counts.keys())
        y = [degree_counts[d] for d in x]

        return self.plot_line(
            x=x,
            y=y,
            title="Degree Distribution",
            xlabel="Degree",
            ylabel="Count",
            color="magenta",
            marker="braille"
        )


def create_sparkline(values: List[float], width: int = 20) -> str:
    """
    Create mini sparkline for inline display.

    Args:
        values: Values to plot
        width: Character width

    Returns:
        Unicode sparkline string
    """
    if not values or len(values) < 2:
        return "─" * width

    # Normalize to 0-7 range (8 levels)
    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return "▄" * width

    # Unicode block characters for sparklines
    chars = " ▁▂▃▄▅▆▇█"

    # Resample values to fit width
    step = len(values) / width
    resampled = [values[int(i * step)] for i in range(width)]

    # Normalize and convert to characters
    normalized = [(v - min_val) / (max_val - min_val) for v in resampled]
    sparkline = "".join(chars[int(n * 7)] for n in normalized)

    return sparkline


def create_progress_bar(current: int, total: int, width: int = 30, show_percent: bool = True) -> str:
    """
    Create progress bar.

    Args:
        current: Current value
        total: Total value
        width: Bar width
        show_percent: Show percentage

    Returns:
        Progress bar string
    """
    if total == 0:
        percent = 0
    else:
        percent = current / total

    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    if show_percent:
        return f"{bar} {percent*100:.1f}%"
    else:
        return bar
