# 🧠 Network Science Agent - Comprehensive Design Document

**Project:** Research Graph Explorer - Phase 3
**Goal:** True agentic system for network science analysis with goal-oriented behavior
**Inspiration:** Claude Code's UX + Claude Agents SDK architecture

---

## Executive Summary

We're building a **truly agentic network science research assistant** that:

✅ **Has agency** - Not just LLM chains, but goal-oriented autonomous behavior
✅ **Asks for clarification** - Goes back to user when needed
✅ **Plans and reflects** - Uses TodoWrite to make thinking visible
✅ **Queries knowledge graphs** - Network science expert with custom tools
✅ **Beautiful terminal UX** - Inspired by Claude Code's elegance
✅ **Distributed easily** - Single command installation like Claude Code

---

## Current State Analysis

### ✅ What We Have (Phases 1 & 2)

**Phase 1: Discovery Engine**
- Frontier-based paper discovery
- Multi-source fetching (Semantic Scholar, arXiv)
- Relevance scoring with LLMs
- Citation network traversal

**Phase 2: Knowledge Extraction**
- PDF downloading and text extraction
- LangExtract ontology-based extraction
- Knowledge graph construction (NetworkX)
- Basic graph operations (save/load, subgraph, entity merging)

**Infrastructure:**
- Data models (Paper, Ontology, Entity, Relationship)
- LLM clients (Anthropic, OpenAI)
- Caching system
- CLI with Rich output

### ❌ What We're Missing (Phase 3)

**Advanced Graph Algorithms:**
- Community detection (Louvain, Leiden, label propagation)
- Centrality measures (PageRank, betweenness, closeness, eigenvector)
- Path analysis (shortest paths, all paths between concepts)
- Gap detection (concepts that should be connected but aren't)
- Echo chamber detection (citation rings, self-referential clusters)
- Author network analysis
- Temporal analysis (research trends over time)

**Agentic System:**
- Goal-oriented agent (not just CLI commands)
- Natural language query interface
- Agent can ask user for clarification
- TodoWrite integration for transparency
- Planning and reflection capabilities
- Memory system (recall previous analyses)

**Terminal UX:**
- Interactive chat mode
- Streaming responses
- Beautiful visualizations of networks
- Progress indicators for long operations
- Command history and shortcuts

---

## Architecture Design

### 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Network Science Agent (Single Agent Loop)          │
├─────────────────────────────────────────────────────────────────┤
│  System Prompt: "You are a network science research assistant"│
│  Context: RESEARCH.md + Previous conversation + Knowledge graph │
│  Tools: 15 custom tools for graph analysis                     │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────┐ ┌──────────────┐
    │ Graph Analysis  │ │ Discovery   │ │ Visualization│
    │ Tools (NEW)     │ │ Tools       │ │ Tools        │
    ├─────────────────┤ ├─────────────┤ ├──────────────┤
    │ - DetectGaps    │ │ - Discover  │ │ - ExportGephi│
    │ - FindEchoCham..│ │ - Extract   │ │ - PlotNetwork│
    │ - CalcCentral.. │ │ - FetchPDF  │ │ - ShowMetrics│
    │ - DetectCommun..│ │ - SearchAPI │ │ - ShowTree   │
    │ - AnalyzePaths  │ └─────────────┘ └──────────────┘
    │ - AuthorNetwork │
    │ - TemporalTrend │
    │ - QueryGraph    │
    └─────────────────┘
              │
              ▼
    ┌─────────────────┐
    │ Memory System   │
    ├─────────────────┤
    │ - Conversation  │
    │ - Analysis      │
    │ - Insights      │
    └─────────────────┘
              │
              ▼
    ┌─────────────────┐
    │ Knowledge Graph │
    │ (NetworkX/Neo4j)│
    └─────────────────┘
```

### 2. Agent Loop Pattern

**Goal-Oriented Execution:**

```python
User Query: "Find gaps in the graph neural networks literature"
    ↓
Agent Planning Phase:
    1. Understand what constitutes a "gap"
    2. Decide which algorithms to use
    3. Create TodoWrite plan
    ↓
Agent Execution Phase (Loop):
    1. Load knowledge graph → QueryGraphTool
    2. Detect communities → DetectCommunitiesTool
    3. Calculate centrality → CalcCentralityTool
    4. Find disconnected important concepts → DetectGapsTool
    5. Generate report → (LLM synthesis)
    ↓
Agent Reflection Phase:
    - Does this answer the question?
    - Should I ask for clarification?
    - Need more analysis?
    ↓
Output to User / Ask for Clarification
```

**Key Insight from Research:**
> Agent asks for clarification by simply **outputting text WITHOUT calling tools**.
> The loop naturally stops and waits for user input. No special tool needed!

### 3. Tool Design

Based on Claude Agents SDK research, we need **tools, not workflows**.

#### Core Philosophy:
- **Atomic operations** - Each tool does ONE thing well
- **Composable** - Agent combines tools to achieve goals
- **Stateless** - Tools don't maintain state (graph does)
- **Error-tolerant** - Graceful failure with helpful messages

#### Tool Categories:

**Category 1: Graph Query Tools**
```python
class QueryGraphTool:
    """Query the knowledge graph using natural language or Cypher"""
    name = "query_graph"
    description = """
    Query the knowledge graph to find papers, entities, relationships.

    Examples:
    - "Find all papers about transformers"
    - "Show entities of type 'Method' related to 'BERT'"
    - "List papers citing the attention mechanism paper"
    """

    async def __call__(self, query: str, graph_id: str) -> dict:
        # Convert NL query to graph query using LLM
        # Execute on NetworkX graph
        # Return structured results
        pass
```

**Category 2: Network Analysis Tools**
```python
class DetectCommunitiesTool:
    """Detect communities in citation or concept network"""
    name = "detect_communities"
    description = """
    Find clusters/communities in the network using algorithms:
    - louvain (default, fast)
    - leiden (more accurate)
    - label_propagation (simpler)

    Returns community assignments and statistics.
    """

    async def __call__(
        self,
        graph_id: str,
        layer: str = "paper",  # "paper" or "concept"
        algorithm: str = "louvain",
        resolution: float = 1.0
    ) -> dict:
        # Load graph
        # Run community detection
        # Return communities with stats
        pass

class CalcCentralityTool:
    """Calculate centrality metrics for nodes"""
    name = "calculate_centrality"
    description = """
    Calculate centrality measures:
    - degree: Number of connections
    - betweenness: Bridge between communities
    - closeness: Average distance to all nodes
    - pagerank: Importance based on citations
    - eigenvector: Importance of neighbors

    Returns top-k nodes by selected metric.
    """

    async def __call__(
        self,
        graph_id: str,
        layer: str = "paper",
        metric: str = "pagerank",
        top_k: int = 10
    ) -> dict:
        pass

class DetectGapsTool:
    """Find literature gaps - missing connections"""
    name = "detect_gaps"
    description = """
    Find gaps in the literature:

    Types of gaps:
    1. Disconnected important concepts (should be related but aren't)
    2. Under-explored areas (low research activity but high importance)
    3. Missing methodological applications
    4. Temporal gaps (research stopped but problem unsolved)

    Uses community structure, centrality, and temporal analysis.
    """

    async def __call__(
        self,
        graph_id: str,
        gap_type: str = "all",
        min_importance: float = 0.5
    ) -> dict:
        # Algorithm:
        # 1. Find high-centrality but low-degree nodes (important but isolated)
        # 2. Find concept pairs that should be connected based on similarity
        # 3. Find temporal gaps (activity dropped but citations still high)
        # 4. Find methodological gaps (method X used for Y but not Z)
        pass

class FindEchoChambersTool:
    """Detect citation rings and echo chambers"""
    name = "find_echo_chambers"
    description = """
    Detect echo chambers and citation manipulation:

    Patterns:
    1. Citation rings (A cites B, B cites C, C cites A disproportionately)
    2. Self-citation clusters (high internal citation ratio)
    3. Isolated highly-cited clusters (disconnect from broader field)
    4. Suspicious citation patterns (anomalous growth)
    """

    async def __call__(
        self,
        graph_id: str,
        min_cluster_size: int = 5,
        threshold: float = 0.7
    ) -> dict:
        # Algorithm:
        # 1. Detect strongly connected components
        # 2. Calculate internal vs external citation ratio
        # 3. Detect cycles in citation graph
        # 4. Flag suspicious patterns
        pass
```

**Category 3: Author & Temporal Analysis**
```python
class AnalyzeAuthorNetworkTool:
    """Analyze author collaboration patterns"""
    name = "analyze_authors"
    description = """
    Analyze author network:
    - Co-authorship patterns
    - Influential authors (by centrality)
    - Research groups (communities)
    - Cross-pollination between groups
    """

    async def __call__(self, graph_id: str) -> dict:
        pass

class AnalyzeTemporalTrendsTool:
    """Analyze research trends over time"""
    name = "analyze_trends"
    description = """
    Analyze how research topics evolve:
    - Emerging topics (increasing attention)
    - Declining topics (decreasing attention)
    - Burst detection (sudden interest spikes)
    - Topic evolution (how concepts change over time)
    """

    async def __call__(
        self,
        graph_id: str,
        time_window: str = "yearly",
        min_papers: int = 5
    ) -> dict:
        pass
```

**Category 4: Path Analysis**
```python
class AnalyzePathsTool:
    """Find and analyze paths between concepts/papers"""
    name = "analyze_paths"
    description = """
    Find connections between papers or concepts:
    - Shortest path (most direct connection)
    - All paths up to length N
    - Influential bridge papers (betweenness)
    - Knowledge flow analysis
    """

    async def __call__(
        self,
        graph_id: str,
        source: str,
        target: str,
        max_length: int = 5
    ) -> dict:
        pass
```

**Category 5: Discovery & Extraction (Existing)**
```python
class DiscoverPapersTool:
    """Discover papers for research question (Phase 1)"""
    pass

class ExtractKnowledgeTool:
    """Extract entities from papers (Phase 2)"""
    pass
```

**Category 6: Visualization & Export**
```python
class ExportGephiTool:
    """Export graph for Gephi visualization"""
    pass

class PlotNetworkTool:
    """Generate terminal-friendly network visualization"""
    name = "plot_network"
    description = """
    Create visual representation of network:
    - ASCII art for terminal
    - Tree view (Rich library)
    - Cluster view with communities highlighted
    """

    async def __call__(
        self,
        graph_id: str,
        layout: str = "tree",  # tree, clusters, timeline
        max_nodes: int = 50
    ) -> str:
        # Generate ASCII/Rich visualization
        pass
```

**Category 7: Memory & Context**
```python
class SaveInsightTool:
    """Save analysis insights to memory"""
    name = "save_insight"
    description = """
    Save findings to memory for later recall:
    - Key insights from analysis
    - Answered research questions
    - Interesting patterns discovered

    Agent can recall these later to provide context.
    """

    async def __call__(self, insight: str, tags: list[str]) -> dict:
        pass

class RecallInsightTool:
    """Recall previous insights"""
    name = "recall_insights"
    description = """
    Retrieve previous insights based on query.
    Useful for maintaining long-term context.
    """

    async def __call__(self, query: str) -> list[str]:
        pass
```

---

## Agent System Prompt

```python
NETWORK_SCIENCE_AGENT_PROMPT = """
You are a network science research assistant expert in analyzing citation networks
and knowledge graphs from academic literature.

## Your Capabilities

You can:
✓ Query knowledge graphs to find papers, concepts, relationships
✓ Detect research gaps and opportunities
✓ Find echo chambers and citation manipulation
✓ Analyze author collaboration networks
✓ Calculate importance metrics (centrality, PageRank)
✓ Detect research communities
✓ Track research trends over time
✓ Find connections between ideas

## Your Behavior

**Goal-Oriented:**
- When given a question, create a plan using TodoWrite
- Break down complex questions into analysis steps
- Execute the plan systematically

**Ask for Clarification:**
- If the question is ambiguous, ask the user to clarify
- If multiple approaches exist, explain options and ask user to choose
- If results need interpretation, describe findings and ask for guidance

**Be Transparent:**
- Always use TodoWrite for multi-step analyses
- Mark tasks as in_progress before starting
- Complete tasks immediately after finishing
- Show your reasoning and thought process

**Be Precise:**
- Cite specific papers and metrics
- Provide quantitative evidence for claims
- Explain network science concepts when relevant
- Reference specific algorithms used

**Communication Style:**
- Direct and efficient (researchers are busy)
- Use precise academic language but stay accessible
- Provide evidence, not opinions
- Focus on actionable insights

## Example Workflows

**User asks: "Find gaps in graph neural network literature"**

Your approach:
1. Use TodoWrite to create plan:
   - Load and inspect knowledge graph
   - Detect research communities
   - Calculate centrality metrics
   - Identify disconnected important concepts
   - Analyze temporal trends
   - Generate gap report

2. Execute each step, using appropriate tools:
   - QueryGraphTool to load GNN papers
   - DetectCommunitiesTool to find research clusters
   - CalcCentralityTool to find important but isolated concepts
   - DetectGapsTool with gap_type="all"

3. Synthesize findings:
   - List specific gaps with evidence
   - Explain why they're gaps
   - Suggest research opportunities

**User asks: "Are there citation rings in my graph?"**

Your approach:
1. Use FindEchoChambersTool
2. Report specific clusters with:
   - Internal vs external citation ratios
   - List of papers involved
   - Statistical evidence of manipulation
3. Visualize suspicious clusters with PlotNetworkTool

**User asks: "Show me the most influential papers"**

Your approach:
1. Ask clarification: "Influential by which metric? Options:
   - Citations (raw count)
   - PageRank (importance in network)
   - Betweenness (bridge between communities)
   - Temporal impact (citations over time)"
2. Once clarified, use CalcCentralityTool
3. Present top papers with metrics and context

## Important Notes

- You have access to a knowledge graph created in Phases 1-2
- Graph contains papers, citations, entities, and relationships
- All papers have metadata (title, authors, year, venue, abstract)
- Use tools to analyze, don't make assumptions
- If a tool fails, explain the error and suggest alternatives
- Memory tools (SaveInsight, RecallInsight) help maintain context across sessions

Remember: You're a research assistant, not just an answering machine.
Help researchers discover insights they couldn't find manually.
"""
```

---

## Implementation Plan

### Phase 3.1: Advanced Graph Algorithms (Week 1-2)

**Create:** `src/analysis/` module

```
src/analysis/
├── __init__.py
├── graph_algorithms.py      # Core algorithms
├── community_detection.py   # Louvain, Leiden, etc.
├── centrality_metrics.py    # PageRank, betweenness, etc.
├── gap_detection.py         # Custom gap finding algorithms
├── echo_chamber.py          # Citation ring detection
├── author_network.py        # Co-authorship analysis
├── temporal_analysis.py     # Trend detection
└── path_analysis.py         # Path finding and analysis
```

**Key Implementations:**

```python
# src/analysis/graph_algorithms.py
import networkx as nx
import community as community_louvain  # python-louvain
from collections import defaultdict
from typing import Dict, List, Tuple

class GraphAnalyzer:
    """Core graph analysis functionality"""

    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph

    def detect_communities(
        self,
        layer: str = "paper",
        algorithm: str = "louvain",
        resolution: float = 1.0
    ) -> Dict[str, int]:
        """Detect communities in network"""

        graph = self.kg.paper_graph if layer == "paper" else self.kg.concept_graph

        if algorithm == "louvain":
            # Convert to undirected for community detection
            G_undirected = graph.to_undirected()
            communities = community_louvain.best_partition(
                G_undirected,
                resolution=resolution
            )
            return communities

        elif algorithm == "leiden":
            # Leiden algorithm (requires leidenalg + igraph)
            import leidenalg
            import igraph as ig

            # Convert NetworkX to igraph
            G_ig = ig.Graph.from_networkx(graph.to_undirected())
            partition = leidenalg.find_partition(
                G_ig,
                leidenalg.ModularityVertexPartition,
                resolution_parameter=resolution
            )

            # Map back to node IDs
            communities = {
                graph.nodes()[i]: partition.membership[i]
                for i in range(len(graph.nodes()))
            }
            return communities

        elif algorithm == "label_propagation":
            communities_gen = nx.community.label_propagation_communities(
                graph.to_undirected()
            )
            communities = {}
            for i, comm in enumerate(communities_gen):
                for node in comm:
                    communities[node] = i
            return communities

        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def calculate_centrality(
        self,
        layer: str = "paper",
        metric: str = "pagerank",
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Calculate centrality metrics"""

        graph = self.kg.paper_graph if layer == "paper" else self.kg.concept_graph

        if metric == "degree":
            centrality = dict(graph.degree())

        elif metric == "betweenness":
            centrality = nx.betweenness_centrality(graph)

        elif metric == "closeness":
            centrality = nx.closeness_centrality(graph)

        elif metric == "pagerank":
            centrality = nx.pagerank(graph)

        elif metric == "eigenvector":
            centrality = nx.eigenvector_centrality(graph, max_iter=1000)

        else:
            raise ValueError(f"Unknown metric: {metric}")

        # Sort and return top k
        sorted_nodes = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_nodes[:top_k]

    def detect_gaps(
        self,
        gap_type: str = "all",
        min_importance: float = 0.5
    ) -> List[Dict]:
        """Detect literature gaps"""

        gaps = []

        # Type 1: Important but isolated concepts
        if gap_type in ["all", "isolated"]:
            pagerank = nx.pagerank(self.kg.concept_graph)
            degree = dict(self.kg.concept_graph.degree())

            for node, pr_score in pagerank.items():
                if pr_score >= min_importance and degree[node] < 3:
                    entity = self.kg.entities.get(node)
                    gaps.append({
                        "type": "isolated_important_concept",
                        "entity": entity.text if entity else node,
                        "entity_type": entity.entity_type if entity else "unknown",
                        "importance": pr_score,
                        "connections": degree[node],
                        "reason": f"High importance ({pr_score:.3f}) but only {degree[node]} connections"
                    })

        # Type 2: Disconnected communities
        if gap_type in ["all", "disconnected"]:
            communities = self.detect_communities(layer="concept")
            community_graph = self._build_community_graph(communities)

            # Find communities with weak connections
            for comm_id in set(communities.values()):
                external_edges = 0
                internal_edges = 0

                for node, comm in communities.items():
                    if comm == comm_id:
                        for neighbor in self.kg.concept_graph.neighbors(node):
                            if communities[neighbor] == comm_id:
                                internal_edges += 1
                            else:
                                external_edges += 1

                if internal_edges > 10 and external_edges < 3:
                    gaps.append({
                        "type": "disconnected_community",
                        "community_id": comm_id,
                        "size": sum(1 for c in communities.values() if c == comm_id),
                        "internal_edges": internal_edges,
                        "external_edges": external_edges,
                        "reason": f"Large community ({internal_edges} internal edges) with only {external_edges} external connections"
                    })

        # Type 3: Concept pairs that should be connected
        if gap_type in ["all", "missing_links"]:
            # Find high-similarity concepts that aren't connected
            for entity1 in list(self.kg.entities.values())[:100]:  # Sample for performance
                similar = self.kg.find_similar_entities(entity1, limit=5)

                for entity2, similarity in similar:
                    if similarity > 0.7:
                        # Check if connected
                        if not self.kg.concept_graph.has_edge(entity1.entity_id, entity2.entity_id):
                            gaps.append({
                                "type": "missing_link",
                                "entity1": entity1.text,
                                "entity2": entity2.text,
                                "similarity": similarity,
                                "reason": f"Highly similar concepts ({similarity:.3f}) but not connected in literature"
                            })

        return gaps

    def find_echo_chambers(
        self,
        min_cluster_size: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """Detect citation rings and echo chambers"""

        echo_chambers = []

        # Find strongly connected components
        strongly_connected = list(nx.strongly_connected_components(self.kg.paper_graph))

        for component in strongly_connected:
            if len(component) < min_cluster_size:
                continue

            # Calculate internal vs external citations
            internal_citations = 0
            external_citations = 0

            for paper_id in component:
                for ref_id in self.kg.papers[paper_id].references:
                    if ref_id in component:
                        internal_citations += 1
                    else:
                        external_citations += 1

            total_citations = internal_citations + external_citations
            if total_citations == 0:
                continue

            internal_ratio = internal_citations / total_citations

            if internal_ratio >= threshold:
                # Suspicious cluster found
                papers = [self.kg.papers[pid] for pid in component if pid in self.kg.papers]

                echo_chambers.append({
                    "type": "citation_ring",
                    "size": len(component),
                    "papers": [p.title for p in papers[:10]],  # Sample
                    "internal_citations": internal_citations,
                    "external_citations": external_citations,
                    "internal_ratio": internal_ratio,
                    "reason": f"Cluster of {len(component)} papers with {internal_ratio:.1%} internal citations"
                })

        return echo_chambers
```

### Phase 3.2: Agent Integration (Week 3-4)

**Create:** `src/agent/` module

```
src/agent/
├── __init__.py
├── network_science_agent.py  # Main agent class
├── prompts.py                # System prompts
├── tools/                    # Tool implementations
│   ├── __init__.py
│   ├── query_graph.py
│   ├── detect_communities.py
│   ├── calc_centrality.py
│   ├── detect_gaps.py
│   ├── find_echo_chambers.py
│   ├── analyze_authors.py
│   ├── analyze_trends.py
│   ├── analyze_paths.py
│   ├── plot_network.py
│   └── memory.py
└── memory_store.py           # Persistent memory
```

**Key Implementation:**

```python
# src/agent/network_science_agent.py
from claude_agent_sdk import ClaudeSDKClient
from .tools import (
    QueryGraphTool,
    DetectCommunitiesTool,
    CalcCentralityTool,
    DetectGapsTool,
    FindEchoChambersTool,
    AnalyzeAuthorsTool,
    AnalyzeTrendsTool,
    AnalyzePathsTool,
    PlotNetworkTool,
    SaveInsightTool,
    RecallInsightTool,
)
from .prompts import NETWORK_SCIENCE_AGENT_PROMPT
from ..extraction.knowledge_graph import KnowledgeGraph

class NetworkScienceAgent:
    """Goal-oriented network science research assistant"""

    def __init__(self, knowledge_graph_path: str):
        """Initialize agent with knowledge graph"""

        # Load knowledge graph
        self.kg = KnowledgeGraph.load(knowledge_graph_path)

        # Initialize tools
        self.tools = [
            QueryGraphTool(self.kg),
            DetectCommunitiesTool(self.kg),
            CalcCentralityTool(self.kg),
            DetectGapsTool(self.kg),
            FindEchoChambersTool(self.kg),
            AnalyzeAuthorsTool(self.kg),
            AnalyzeTrendsTool(self.kg),
            AnalyzePathsTool(self.kg),
            PlotNetworkTool(self.kg),
            SaveInsightTool(),
            RecallInsightTool(),
        ]

        # Initialize SDK client
        self.client = None

    async def start_session(self):
        """Start interactive session"""
        self.client = ClaudeSDKClient(
            system_prompt=NETWORK_SCIENCE_AGENT_PROMPT,
            tools=self.tools,
        )
        await self.client.__aenter__()

    async def end_session(self):
        """End interactive session"""
        if self.client:
            await self.client.__aexit__(None, None, None)

    async def query(self, user_query: str):
        """
        Process a user query with goal-oriented behavior.

        The agent will:
        1. Understand the goal
        2. Create a plan (using TodoWrite)
        3. Execute tools autonomously
        4. Ask for clarification if needed
        5. Synthesize findings

        Args:
            user_query: Natural language research question

        Yields:
            Messages from the agent (text, tool calls, results)
        """

        if not self.client:
            await self.start_session()

        # Send query to agent
        await self.client.query(user_query)

        # Stream responses
        async for message in self.client.receive_response():
            yield message

    async def continue_conversation(self, user_response: str):
        """
        Continue conversation after agent asks for clarification.

        Args:
            user_response: User's response to agent's question

        Yields:
            Messages from the agent
        """

        await self.client.query(user_response)
        async for message in self.client.receive_response():
            yield message
```

### Phase 3.3: Terminal UX (Week 5-6)

**Create:** Beautiful interactive CLI with Rich

```python
# src/cli/chat.py
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

from ..agent.network_science_agent import NetworkScienceAgent

console = Console()

async def chat_mode(knowledge_graph_path: str):
    """Interactive chat with network science agent"""

    # Welcome
    console.print(Panel.fit(
        "[bold cyan]Network Science Research Assistant[/bold cyan]\n\n"
        "Ask me questions about your research graph:\n"
        "• Find literature gaps\n"
        "• Detect echo chambers\n"
        "• Analyze author networks\n"
        "• Track research trends\n\n"
        "Type 'exit' to quit, 'help' for examples",
        border_style="cyan"
    ))

    # Initialize agent
    console.print("\n[dim]Loading knowledge graph...[/dim]")
    agent = NetworkScienceAgent(knowledge_graph_path)
    await agent.start_session()
    console.print("[green]✓[/green] Agent ready!\n")

    # Create prompt session with history
    session = PromptSession(
        history=FileHistory('.rge_history'),
        multiline=False,
    )

    try:
        while True:
            # Get user input
            try:
                user_input = await session.prompt_async("You: ")
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if not user_input.strip():
                continue

            if user_input.lower() in ['exit', 'quit']:
                break

            if user_input.lower() == 'help':
                show_help()
                continue

            # Send to agent and stream response
            console.print("\n[bold cyan]Agent:[/bold cyan]", end=" ")

            response_text = ""

            async for message in agent.query(user_input):
                # Handle different message types
                if isinstance(message, TextBlock):
                    # Stream text token by token
                    response_text += message.text
                    console.print(message.text, end="")

                elif isinstance(message, ToolUseBlock):
                    # Show tool being used
                    console.print(f"\n[dim]→ Using {message.tool_name}...[/dim]")

                elif isinstance(message, ToolResultBlock):
                    # Show tool result (formatted)
                    if message.tool_name == "TodoWrite":
                        display_todos(message.result)
                    elif message.tool_name == "plot_network":
                        console.print(message.result)
                    else:
                        # Don't show raw tool results, let agent synthesize
                        pass

            console.print("\n")

    finally:
        await agent.end_session()
        console.print("\n[cyan]Goodbye! Happy researching! 🚀[/cyan]\n")

def display_todos(todos: list):
    """Display TodoWrite status with Rich"""
    from rich.table import Table

    table = Table(title="📋 Analysis Plan", show_header=True)
    table.add_column("Status", style="cyan", width=12)
    table.add_column("Task", style="white")

    for todo in todos:
        status = todo["status"]
        if status == "completed":
            icon = "[green]✓[/green]"
        elif status == "in_progress":
            icon = "[yellow]⟳[/yellow]"
        else:
            icon = "[dim]○[/dim]"

        text = todo.get("activeForm" if status == "in_progress" else "content")
        table.add_row(icon, text)

    console.print(table)

def show_help():
    """Show example queries"""
    help_text = """
# Example Queries

**Finding Gaps:**
- "Find gaps in the graph neural networks literature"
- "What concepts are underexplored in my domain?"
- "Show me important but isolated concepts"

**Echo Chambers:**
- "Are there citation rings in my graph?"
- "Find clusters with high self-citation"
- "Detect echo chambers"

**Influence:**
- "Who are the most influential authors?"
- "What are the most important papers by PageRank?"
- "Show me bridge papers connecting communities"

**Communities:**
- "Find research communities in my graph"
- "How are research groups organized?"
- "Show me the structure of the field"

**Trends:**
- "What topics are emerging?"
- "Track transformer research over time"
- "Show me declining research areas"

**Connections:**
- "How is paper A connected to paper B?"
- "Find all paths between 'BERT' and 'attention mechanism'"
    """

    console.print(Markdown(help_text))
```

### Phase 3.4: Distribution (Week 7-8)

**Setup for easy installation:**

```bash
# Install script
curl -fsSL https://raw.githubusercontent.com/yourusername/research-graph-explorer/main/install.sh | bash

# Or via pip
pip install research-graph-explorer

# Or via pipx (recommended)
pipx install research-graph-explorer
```

**Usage:**

```bash
# Phase 1: Discover papers
rge discover "graph neural networks" --max-papers 100 --output papers.json

# Phase 2: Extract knowledge
rge extract papers.json --ontology ml_research.yaml --output kg.json

# Phase 3: Interactive analysis (NEW!)
rge chat kg.json

> Find gaps in the literature
> Are there citation rings?
> Show me the most influential papers
> exit
```

---

## Key Design Decisions

### 1. Single Agent Loop (Not Multi-Agent)

**Why:**
- Simplicity - easier to debug and maintain
- Claude Code uses single agent successfully
- Complexity should be in tools, not orchestration
- User maintains single conversation thread

**When to use subagents:**
- Parallel analysis (3+ independent tasks)
- Specialized domains (could add subagent for biology vs CS)
- Future: Meta-analysis across multiple graphs

### 2. Tools Not Workflows

**Why:**
- Agent decides how to compose tools
- Flexible to handle novel questions
- User doesn't need to learn workflows
- Tools are testable units

**Pattern:**
```python
# ✅ Good: Atomic tools
DetectGapsTool
FindEchoChambersTool
CalcCentralityTool

# ❌ Bad: Workflow tool
AnalyzeLiteratureTool  # Does everything, inflexible
```

### 3. TodoWrite for Transparency

**Critical:**
- Every multi-step analysis MUST use TodoWrite
- Agent marks in_progress before starting
- Agent completes immediately after finishing
- User always knows what's happening

### 4. Ask for Clarification

**Pattern:**
Agent outputs text without calling tools:

```
Agent: "To find influential papers, I can use several metrics:
1. Citations (raw count)
2. PageRank (importance in network)
3. Betweenness (bridge between communities)

Which metric would you prefer?"

[Agent stops, waits for user input]

User: "PageRank"

Agent: [calls CalcCentralityTool with metric="pagerank"]
```

### 5. Memory for Long-Term Context

**Pattern:**
- Agent uses SaveInsightTool when finding important patterns
- RecallInsightTool provides context for future queries
- Stored in JSON file: `~/.rge/memory.json`

Example:
```python
# After detecting a gap
await SaveInsightTool(
    insight="Found 5 important but isolated concepts in GNN literature",
    tags=["gap", "GNN", "isolated_concepts"]
)

# Later query: "What gaps did we find?"
await RecallInsightTool(query="gaps in GNN")
# Returns previous finding
```

---

## Success Metrics

**Week 4:**
✅ Agent can answer: "Find gaps in my literature"
✅ Uses TodoWrite to show plan
✅ Returns specific gaps with evidence
✅ Beautiful terminal output

**Week 8:**
✅ Interactive chat mode working
✅ Agent asks for clarification when needed
✅ All 11 tools implemented and tested
✅ Can handle complex multi-step analyses
✅ Memory system preserves insights

**Week 12:**
✅ Distributed via PyPI
✅ One-line installer
✅ Documentation complete
✅ Real users analyzing their research graphs

---

## Technical Stack

**Agent Framework:**
```
claude-agent-sdk = "^0.1.0"  # Agent SDK
anthropic = "^0.40.0"         # LLM backend
```

**Graph Analysis:**
```
networkx = "^3.4"             # Graph algorithms
python-louvain = "^0.16"      # Community detection
leidenalg = "^0.10.0"         # Better community detection
igraph = "^0.11.0"            # Fast graph library
```

**Terminal UX:**
```
rich = "^13.7.0"              # Beautiful terminal output
prompt-toolkit = "^3.0.0"     # Interactive prompts
click = "^8.1.0"              # CLI framework
```

**Data:**
```
pydantic = "^2.0"             # Data validation
```

---

## Next Steps

1. ✅ Review this design document
2. ⏭️ Implement Phase 3.1: Advanced graph algorithms
3. ⏭️ Implement Phase 3.2: Agent integration
4. ⏭️ Implement Phase 3.3: Terminal UX
5. ⏭️ Test with real research graphs
6. ⏭️ Package and distribute

---

## Conclusion

This design brings together:
- **True agency** from Claude Agents SDK architecture
- **Beautiful UX** inspired by Claude Code
- **Domain expertise** in network science
- **Your existing work** from Phases 1 & 2

The result: A **goal-oriented network science research assistant** that researchers will love to use.

Built with simplicity, transparency, and user delight at the core.

Let's build something amazing! 🚀
