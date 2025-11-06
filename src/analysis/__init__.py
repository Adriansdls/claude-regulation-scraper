"""
Analysis module - Phase 3 of Research Graph Explorer.

Provides:
1. Pre-defined graph algorithms (fast, tested, safe)
2. Dynamic code execution (flexible, handles novel queries)

The hybrid approach gives us:
- Speed for common operations (pre-defined algorithms)
- Flexibility for novel analyses (LLM-generated code)
- Safety through sandboxing and validation
"""

from .graph_algorithms import (
    GraphAnalyzer,
    CommunityResult,
    CentralityResult,
    GapResult,
    EchoChamberResult,
)

from .dynamic_executor import (
    DynamicGraphQueryExecutor,
    SafeExecutor,
    ExecutionResult,
)

__all__ = [
    # Main classes
    "GraphAnalyzer",
    "DynamicGraphQueryExecutor",
    "SafeExecutor",

    # Result types
    "CommunityResult",
    "CentralityResult",
    "GapResult",
    "EchoChamberResult",
    "ExecutionResult",
]
