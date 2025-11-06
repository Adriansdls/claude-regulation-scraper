"""Agent module - Phase 3.2 of Research Graph Explorer.

Provides truly agentic system for network science analysis with:
- Goal-oriented behavior (not just LLM chains)
- Autonomous tool use
- Natural clarification asking
- Memory across sessions
- Transparent reasoning
"""

from .network_science_agent import NetworkScienceAgent
from .prompts import NETWORK_SCIENCE_AGENT_PROMPT, NETWORK_SCIENCE_AGENT_PROMPT_SHORT

__all__ = [
    "NetworkScienceAgent",
    "NETWORK_SCIENCE_AGENT_PROMPT",
    "NETWORK_SCIENCE_AGENT_PROMPT_SHORT",
]
