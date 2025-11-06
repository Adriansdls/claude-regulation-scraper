"""Network Science Agent - Goal-oriented research assistant.

A truly agentic system (not just LLM chains) that:
- Plans how to answer questions
- Uses tools autonomously
- Asks for clarification when needed
- Has memory across sessions
- Shows its thinking process

Implementation note: This uses the Anthropic API directly in an agentic pattern.
When Claude Agents SDK becomes available on PyPI, this can be upgraded to use it.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from anthropic import AsyncAnthropic

from ..extraction import KnowledgeGraph
from ..analysis import GraphAnalyzer, DynamicGraphQueryExecutor
from .prompts import NETWORK_SCIENCE_AGENT_PROMPT
from .tools import (
    DetectCommunitiesTool,
    CalculateCentralityTool,
    DetectGapsTool,
    FindEchoChambersTool,
    AnalyzePathsTool,
    AnalyzeAuthorNetworkTool,
    DynamicGraphQueryTool,
    GetGraphInfoTool,
    ShowGraphStatsTool,
    VisualizeNetworkTool,
    SaveInsightTool,
    RecallInsightsTool,
)
from .tools.memory_tools import MemoryStore


class NetworkScienceAgent:
    """
    Goal-oriented network science research assistant.

    This is a TRUE agentic system with:
    - Autonomous tool use
    - Goal-oriented behavior (plans and executes)
    - Natural clarification asking (outputs text without tools)
    - Memory across sessions
    - Transparent reasoning

    Not just LLM chains - this has agency!
    """

    def __init__(
        self,
        knowledge_graph_path: str,
        api_key: Optional[str] = None,
        model: str = "claude-3-7-sonnet-20250219"  # Updated to working model (Feb 2025)
    ):
        """
        Initialize agent with knowledge graph.

        Args:
            knowledge_graph_path: Path to knowledge graph JSON
            api_key: Anthropic API key (if None, reads from env)
            model: Claude model to use
        """
        # Load knowledge graph
        self.kg = KnowledgeGraph.load(knowledge_graph_path)

        # Initialize analyzers
        self.analyzer = GraphAnalyzer(self.kg)
        self.dynamic_executor = DynamicGraphQueryExecutor(self.kg)

        # Initialize memory
        self.memory = MemoryStore()

        # Initialize tools
        self.tools = self._setup_tools()

        # Initialize Anthropic client
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

        # Conversation history
        self.messages = []

    def _setup_tools(self) -> List:
        """Set up all agent tools."""
        return [
            DetectCommunitiesTool(self.analyzer),
            CalculateCentralityTool(self.analyzer),
            DetectGapsTool(self.analyzer),
            FindEchoChambersTool(self.analyzer),
            AnalyzePathsTool(self.analyzer),
            AnalyzeAuthorNetworkTool(self.analyzer),
            DynamicGraphQueryTool(self.dynamic_executor),
            GetGraphInfoTool(self.dynamic_executor),
            ShowGraphStatsTool(self.kg),
            VisualizeNetworkTool(self.kg, self.analyzer),
            SaveInsightTool(self.memory),
            RecallInsightsTool(self.memory),
        ]

    def _tools_to_anthropic_format(self) -> List[Dict]:
        """
        Convert our tools to Anthropic's tool format.

        Returns list of tool schemas for the API.
        """
        tool_schemas = []

        for tool in self.tools:
            # Build parameter schema by inspecting the tool
            schema = {
                "name": tool.name,
                "description": tool.description.strip(),
            }

            # For now, we'll use a simplified parameter schema
            # In production, you'd want to properly define each tool's parameters
            if tool.name == "detect_communities":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "layer": {
                            "type": "string",
                            "enum": ["paper", "concept"],
                            "description": "Which network layer to analyze"
                        },
                        "algorithm": {
                            "type": "string",
                            "enum": ["louvain", "leiden", "label_propagation"],
                            "description": "Community detection algorithm"
                        },
                        "resolution": {
                            "type": "number",
                            "description": "Resolution parameter (higher = more communities)"
                        },
                        "min_size": {
                            "type": "integer",
                            "description": "Minimum community size"
                        }
                    },
                    "required": []
                }
            elif tool.name == "calculate_centrality":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "layer": {
                            "type": "string",
                            "enum": ["paper", "concept"],
                            "description": "Which network layer"
                        },
                        "metric": {
                            "type": "string",
                            "enum": ["pagerank", "betweenness", "closeness", "degree", "eigenvector"],
                            "description": "Centrality metric"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of top nodes to return"
                        }
                    },
                    "required": []
                }
            elif tool.name == "detect_gaps":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "gap_type": {
                            "type": "string",
                            "enum": ["all", "isolated", "disconnected_communities", "missing_links"],
                            "description": "Type of gap to detect"
                        },
                        "min_importance": {
                            "type": "number",
                            "description": "Minimum importance score (0-1)"
                        },
                        "min_connections": {
                            "type": "integer",
                            "description": "Maximum connections for isolated gaps"
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Minimum similarity for missing links"
                        }
                    },
                    "required": []
                }
            elif tool.name == "find_echo_chambers":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "min_cluster_size": {
                            "type": "integer",
                            "description": "Minimum papers in suspicious cluster"
                        },
                        "internal_ratio_threshold": {
                            "type": "number",
                            "description": "Minimum internal citation ratio (0-1)"
                        },
                        "min_suspicion_score": {
                            "type": "number",
                            "description": "Minimum suspicion score to report (0-1)"
                        }
                    },
                    "required": []
                }
            elif tool.name == "analyze_paths":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "source_id": {
                            "type": "string",
                            "description": "Source paper or concept ID"
                        },
                        "target_id": {
                            "type": "string",
                            "description": "Target paper or concept ID"
                        },
                        "max_paths": {
                            "type": "integer",
                            "description": "Maximum paths to find"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum path length"
                        }
                    },
                    "required": ["source_id", "target_id"]
                }
            elif tool.name == "analyze_author_network":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "top_k": {
                            "type": "integer",
                            "description": "Number of top authors to return"
                        }
                    },
                    "required": []
                }
            elif tool.name == "dynamic_graph_query":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "NetworkX Python code to execute (must set 'result' variable)"
                        },
                        "description": {
                            "type": "string",
                            "description": "What the code does (for logging)"
                        }
                    },
                    "required": ["code"]
                }
            elif tool.name == "get_graph_info":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            elif tool.name == "show_graph_stats":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            elif tool.name == "visualize_network":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "view_type": {
                            "type": "string",
                            "enum": ["communities", "tree", "top_papers", "connections"],
                            "description": "Type of visualization"
                        },
                        "max_nodes": {
                            "type": "integer",
                            "description": "Maximum nodes to display"
                        },
                        "focal_node": {
                            "type": "string",
                            "description": "Optional node ID to focus on"
                        }
                    },
                    "required": []
                }
            elif tool.name == "save_insight":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "insight": {
                            "type": "string",
                            "description": "The insight text to save"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional additional metadata"
                        }
                    },
                    "required": ["insight"]
                }
            elif tool.name == "recall_insights":
                schema["input_schema"] = {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Text to search for"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return"
                        }
                    },
                    "required": []
                }

            tool_schemas.append(schema)

        return tool_schemas

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Execute a tool by name with given input.

        Args:
            tool_name: Name of the tool
            tool_input: Tool parameters

        Returns:
            Tool execution result
        """
        # Find the tool
        tool = next((t for t in self.tools if t.name == tool_name), None)

        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }

        try:
            # Call the tool
            result = tool(**tool_input)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def query(self, user_query: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a user query with goal-oriented behavior.

        The agent will:
        1. Understand the goal
        2. Plan approach (may use multiple tools)
        3. Execute tools autonomously
        4. Ask for clarification if needed (by outputting text without tools)
        5. Synthesize findings

        Args:
            user_query: Natural language research question

        Yields:
            Messages from the agent (text, tool calls, results)
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_query
        })

        # Agent loop
        while True:
            # Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=NETWORK_SCIENCE_AGENT_PROMPT,
                messages=self.messages,
                tools=self._tools_to_anthropic_format(),
            )

            # Add assistant response to history
            assistant_message = {
                "role": "assistant",
                "content": response.content
            }
            self.messages.append(assistant_message)

            # Process response content
            has_tool_use = False

            for block in response.content:
                if block.type == "text":
                    # Text output - yield to user
                    yield {
                        "type": "text",
                        "text": block.text
                    }

                elif block.type == "tool_use":
                    has_tool_use = True

                    # Yield tool use notification
                    yield {
                        "type": "tool_use",
                        "tool_name": block.name,
                        "tool_input": block.input
                    }

                    # Execute tool
                    tool_result = await self._execute_tool(block.name, block.input)

                    # Yield tool result
                    yield {
                        "type": "tool_result",
                        "tool_name": block.name,
                        "result": tool_result
                    }

                    # Add tool result to messages for next iteration
                    self.messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result)
                        }]
                    })

            # If no tool use, agent is done (either provided answer or asking for clarification)
            if not has_tool_use:
                break

            # If stop reason is tool_use, continue loop to process results
            if response.stop_reason == "tool_use":
                continue

            # Otherwise, agent is done
            break

    async def continue_conversation(self, user_response: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Continue conversation after agent asked for clarification.

        Args:
            user_response: User's response to agent's question

        Yields:
            Messages from the agent
        """
        # This is the same as query - just continues the conversation
        async for message in self.query(user_response):
            yield message

    def reset(self):
        """Reset conversation history."""
        self.messages = []

    def get_conversation_history(self) -> List[Dict]:
        """Get full conversation history."""
        return self.messages.copy()
