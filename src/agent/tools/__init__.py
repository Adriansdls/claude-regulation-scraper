"""Agent tools for network science analysis.

Each tool wraps a graph algorithm or capability, providing a simple interface
for the agent to use. Tools are designed to be:
- Atomic: Do one thing well
- Composable: Agent combines tools to achieve goals
- Self-descriptive: Clear name and description
- Error-tolerant: Graceful failure with helpful messages
"""

from .graph_tools import (
    DetectCommunitiesTool,
    CalculateCentralityTool,
    DetectGapsTool,
    FindEchoChambersTool,
    AnalyzePathsTool,
    AnalyzeAuthorNetworkTool,
)

from .dynamic_tools import (
    DynamicGraphQueryTool,
    GetGraphInfoTool,
)

from .visualization_tools import (
    ShowGraphStatsTool,
    VisualizeNetworkTool,
)

from .memory_tools import (
    SaveInsightTool,
    RecallInsightsTool,
)

__all__ = [
    # Graph analysis tools
    "DetectCommunitiesTool",
    "CalculateCentralityTool",
    "DetectGapsTool",
    "FindEchoChambersTool",
    "AnalyzePathsTool",
    "AnalyzeAuthorNetworkTool",

    # Dynamic execution
    "DynamicGraphQueryTool",
    "GetGraphInfoTool",

    # Visualization
    "ShowGraphStatsTool",
    "VisualizeNetworkTool",

    # Memory
    "SaveInsightTool",
    "RecallInsightsTool",
]
