# Comprehensive Research Report: Building Agentic Systems with Claude Agent SDK

## Executive Summary

This report provides an in-depth analysis of the Claude Agent SDK (Python) with a focus on building truly agentic systems - goal-oriented agents with autonomy, planning capabilities, and tool use. The research covers core architecture, tool patterns, user interaction, advanced agent patterns, and provides specific guidance for building a network science expert agent that can query knowledge graphs.

**Key Finding**: The fundamental difference between "agentic" systems and simple LLM chains lies in the **feedback loop architecture** (gather context → take action → verify work → repeat) combined with **autonomous decision-making** about which tools to use and when to iterate.

---

## Table of Contents

1. [Core Architecture](#1-core-architecture)
2. [What Makes an Agent "Agentic"](#2-what-makes-an-agent-agentic)
3. [The Agent Loop & Reasoning Pattern](#3-the-agent-loop--reasoning-pattern)
4. [Tool Use Patterns](#4-tool-use-patterns)
5. [User Interaction Patterns](#5-user-interaction-patterns)
6. [Advanced Agent Patterns](#6-advanced-agent-patterns)
7. [State and Memory Management](#7-state-and-memory-management)
8. [Code Examples](#8-code-examples)
9. [Building a Network Science Expert Agent](#9-building-a-network-science-expert-agent)
10. [Best Practices & Anti-Patterns](#10-best-practices--anti-patterns)
11. [Production Deployment](#11-production-deployment)
12. [Resources & Links](#12-resources--links)

---

## 1. Core Architecture

### 1.1 Foundational Design

The Claude Agent SDK is built on top of the agent harness that powers Claude Code. It transforms Claude from a reactive chatbot into a proactive agent with:

**Core Components:**
- **Context Management**: Automatic compaction to prevent context overflow
- **Rich Tool Ecosystem**: File operations, code execution, web search, MCP extensibility
- **Advanced Permissions**: Fine-grained control over agent capabilities
- **Production Essentials**: Built-in error handling, session management, and monitoring
- **Optimized Claude Integration**: Automatic prompt caching

### 1.2 Two Main Interfaces

The SDK provides two primary ways to interact with Claude:

#### a) `query()` - Simple Function

```python
from claude_agent_sdk import query

# Simple one-shot query
async for message in query(prompt="What is 2 + 2?"):
    print(message)
```

**Use Case**: Single-turn conversations, straightforward tasks

#### b) `ClaudeSDKClient` - Full Agent System

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=options) as client:
    # Multi-turn conversation with memory
    await client.query("Find all SQL queries in the codebase")
    async for response in client.receive_response():
        # Process agent responses
        pass

    # Follow-up maintains context
    await client.query("Optimize the slowest one")
    async for response in client.receive_response():
        pass
```

**Use Case**: Multi-turn conversations, custom tools, hooks, state management

### 1.3 Architecture Layers

```
┌─────────────────────────────────────────┐
│         Your Application                │
│  (Network Science Agent, etc.)          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Claude Agent SDK (Python)          │
│  • ClaudeSDKClient                      │
│  • Tool System (MCP)                    │
│  • Hooks System                         │
│  • Context Management                   │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Claude Code (Node.js CLI)          │
│  • Agent Loop                           │
│  • Built-in Tools                       │
│  • Session Management                   │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Claude API (Sonnet 4.5)            │
│  • LLM Reasoning                        │
│  • Extended Thinking                    │
│  • Tool Use                             │
└─────────────────────────────────────────┘
```

---

## 2. What Makes an Agent "Agentic"

### 2.1 The Core Distinction

**LLM Chains (NOT Agentic):**
- Predefined sequence of steps
- Scripted flow: input → LLM → output → next LLM → output
- No autonomous decision-making
- No ability to self-correct
- Reactive only (responds to prompts)

```python
# Example of LLM Chain (NOT agentic)
def llm_chain(query):
    # Step 1: Always extract keywords
    keywords = llm("Extract keywords from: " + query)

    # Step 2: Always search database
    results = database.search(keywords)

    # Step 3: Always summarize
    summary = llm("Summarize: " + results)

    return summary  # Done - no iteration, no decision-making
```

**Agentic Systems:**
- Goal-oriented behavior (works toward objectives)
- Autonomous decision-making (chooses which tools to use)
- Iterative self-correction (verifies work, retries if needed)
- Multi-step planning (breaks goals into sub-tasks)
- Tool orchestration (decides when and how to use tools)
- Feedback loops (gather context → act → verify → repeat)

```python
# Example of Agentic System
async def agentic_system(goal):
    async with ClaudeSDKClient() as client:
        await client.query(goal)

        # Agent autonomously decides:
        # - Which tools to use
        # - When to use them
        # - Whether results are satisfactory
        # - Whether to iterate or ask for clarification
        async for message in client.receive_response():
            # Agent may call multiple tools
            # Agent may verify results
            # Agent may ask clarifying questions
            # Agent stops when goal is achieved
            pass
```

### 2.2 Key Differentiators

| Aspect | LLM Chains | Agentic Systems |
|--------|-----------|----------------|
| **Control Flow** | Predefined, scripted | Dynamic, adaptive |
| **Decision Making** | Developer hardcodes logic | Agent decides autonomously |
| **Tool Selection** | Always same sequence | Agent chooses based on context |
| **Error Handling** | Manual retry logic | Self-correction through iteration |
| **Goal Achievement** | Executes steps | Verifies goal completion |
| **Planning** | None (follows script) | Multi-step planning and replanning |

### 2.3 The Critical Principle

> "Give your agents a computer, allowing them to work like humans do."

Access to:
- File systems
- Terminal execution
- External tools
- Ability to verify their own work

...transforms LLMs from passive responders into active agents that can **iterate on their own output** and **adapt to feedback**.

---

## 3. The Agent Loop & Reasoning Pattern

### 3.1 The Core Feedback Loop

At the heart of every agentic system is this cycle:

```
┌─────────────────┐
│ Gather Context  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Take Action    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Verify Work    │
└────────┬────────┘
         │
         ▼
    ┌───────┐
    │Repeat?│──Yes──┐
    └───┬───┘       │
        │           │
        No          │
        │           │
        ▼           │
    ┌──────┐        │
    │ Done │        │
    └──────┘        │
        │           │
        └───────────┘
```

### 3.2 The Technical Loop

From a technical perspective, Claude Code implements this pattern:

```python
# Simplified agent loop (conceptual)
while True:
    # Claude generates a message
    message = await claude.generate()

    # If message includes tool calls
    if message.has_tool_use():
        # Execute tools
        tool_results = execute_tools(message.tool_calls)

        # Feed results back to Claude
        continue

    # If message is just text (no tool calls)
    else:
        # Agent is done or asking for clarification
        # Loop stops, waits for user input
        output_to_user(message.text)
        break
```

**Key Insight**: The agent can ask for clarification by simply outputting text without calling tools. The loop naturally pauses for user input.

### 3.3 Extended Thinking & Reflection

Claude 4's interleaved thinking enables:
- Reflection after each tool call
- Dynamic plan adjustment
- Error detection and correction
- Multi-step reasoning

**Pattern:**
```
1. Think: "I need to find network centrality for this graph"
2. Act: Call graph_query tool
3. Reflect: "The results show high centrality. Is this expected?"
4. Think: "I should verify by checking node degrees"
5. Act: Call degree_distribution tool
6. Reflect: "Results are consistent. I can provide answer."
7. Act: Respond to user with findings
```

### 3.4 ReAct-Like Pattern

Best practice is to adopt a ReAct-like loop with explicit stop conditions:

```
Observe → Think → Act → Check → (Stop or Repeat)
```

- **Observe**: Intake message + relevant history
- **Think**: Choose the next tool with justification
- **Act**: Invoke the tool with validated params
- **Check**: Verify outputs meet constraints; retry or escalate if needed
- **Stop**: When acceptance criteria are met

---

## 4. Tool Use Patterns

### 4.1 Model Context Protocol (MCP)

MCP is the standard mechanism for extending agents with custom tools. It provides a protocol for:
- Tool discovery
- Tool invocation
- Resource management
- Authentication

**Architecture:**

```
┌─────────────────┐
│  MCP Host       │ ← Your application
│  (SDK Client)   │
└────────┬────────┘
         │
         ├──────────┐
         │          │
    ┌────▼────┐  ┌──▼──────┐
    │ MCP     │  │ MCP     │
    │ Server  │  │ Server  │
    │ (DB)    │  │ (Graph) │
    └─────────┘  └─────────┘
```

### 4.2 Creating Custom Tools

#### In-Process SDK MCP Server (Recommended)

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

# Define tools with @tool decorator
@tool(
    name="query_graph",
    description="Query the knowledge graph using Cypher",
    params={
        "query": {"type": "string", "description": "Cypher query to execute"},
        "limit": {"type": "number", "description": "Max results", "default": 10}
    }
)
async def query_graph(args):
    """Execute a Cypher query against Neo4j knowledge graph."""
    query = args["query"]
    limit = args.get("limit", 10)

    # Execute query (example with Neo4j driver)
    from neo4j import AsyncGraphDatabase
    async with driver.session() as session:
        result = await session.run(query + f" LIMIT {limit}")
        records = await result.data()

    return {
        "content": [
            {
                "type": "text",
                "text": f"Query returned {len(records)} results:\n" +
                        json.dumps(records, indent=2)
            }
        ]
    }

@tool(
    name="calculate_centrality",
    description="Calculate network centrality metrics (degree, betweenness, closeness)",
    params={
        "metric": {"type": "string", "enum": ["degree", "betweenness", "closeness"]},
        "node_id": {"type": "string", "description": "Optional specific node ID"}
    }
)
async def calculate_centrality(args):
    """Calculate centrality metrics for network analysis."""
    metric = args["metric"]
    node_id = args.get("node_id")

    # Your network analysis logic here
    results = perform_centrality_calculation(metric, node_id)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Centrality analysis ({metric}):\n" + json.dumps(results, indent=2)
            }
        ]
    }

# Create SDK MCP server with your tools
graph_tools = create_sdk_mcp_server(
    name="network-science-tools",
    version="1.0.0",
    tools=[query_graph, calculate_centrality]
)

# Configure agent options
options = ClaudeAgentOptions(
    mcp_servers={
        "graph": graph_tools
    },
    allowed_tools=[
        "mcp__graph__query_graph",
        "mcp__graph__calculate_centrality"
    ]
)

# Use with agent
async with ClaudeSDKClient(options=options) as client:
    await client.query("What are the most central nodes in the network?")
    async for message in client.receive_response():
        print(message)
```

### 4.3 Tool Design Best Practices

#### "Less is More" Principle

Context window space is your most valuable resource. Design tools that:
- Minimize context usage
- Maximize relevant information delivery
- Return conversational updates, not technical dumps

**Bad Tool Design:**
```python
@tool("dump_database", "Dump entire database")
async def dump_database(args):
    # Returns 100MB of data - wastes context!
    return {"content": [{"type": "text", "text": database.dump_all()}]}
```

**Good Tool Design:**
```python
@tool("search_database", "Search database with filters")
async def search_database(args):
    # Returns only relevant results
    query = args["query"]
    filters = args.get("filters", {})
    results = database.search(query, filters, limit=10)

    # Summarize, don't dump
    summary = f"Found {len(results)} matching records. Top results:\n"
    for r in results[:5]:
        summary += f"- {r['title']}: {r['summary']}\n"

    return {"content": [{"type": "text", "text": summary}]}
```

#### Workflow-Based Tools

Design tools around workflows, not raw APIs:

**Bad: API Mirror**
```python
@tool("http_post", "Make HTTP POST request")
@tool("http_get", "Make HTTP GET request")
@tool("parse_json", "Parse JSON response")
# Agent must orchestrate multiple low-level calls
```

**Good: Workflow Tool**
```python
@tool("fetch_paper_citations", "Fetch citations for a research paper")
async def fetch_paper_citations(args):
    # Handles complete workflow internally
    paper_id = args["paper_id"]

    # 1. Fetch paper metadata
    metadata = await api.get_paper(paper_id)

    # 2. Get citations
    citations = await api.get_citations(paper_id)

    # 3. Format for agent
    result = format_citations(metadata, citations)

    return {"content": [{"type": "text", "text": result}]}
```

#### Tool Naming Convention

MCP tools follow the pattern: `mcp__<server>__<tool>`

Example: `mcp__graph__query_cypher`

### 4.4 Complex Data Structures

Tools can handle complex inputs and outputs:

```python
@tool(
    name="analyze_network_community",
    description="Detect and analyze communities in a network",
    params={
        "algorithm": {
            "type": "string",
            "enum": ["louvain", "label_propagation", "girvan_newman"],
            "description": "Community detection algorithm"
        },
        "parameters": {
            "type": "object",
            "description": "Algorithm-specific parameters",
            "properties": {
                "resolution": {"type": "number"},
                "iterations": {"type": "number"}
            }
        }
    }
)
async def analyze_network_community(args):
    algorithm = args["algorithm"]
    params = args.get("parameters", {})

    # Complex computation
    communities = detect_communities(algorithm, **params)

    # Return structured data
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "algorithm": algorithm,
                    "num_communities": len(communities),
                    "modularity": calculate_modularity(communities),
                    "communities": [
                        {
                            "id": i,
                            "size": len(c),
                            "top_nodes": list(c)[:5]
                        }
                        for i, c in enumerate(communities)
                    ]
                }, indent=2)
            }
        ]
    }
```

### 4.5 Can Agents Create/Modify Tools Dynamically?

**Short answer**: Not directly, but you can enable it indirectly.

**Pattern: Meta-Tool for Code Generation**

```python
@tool(
    name="create_analysis_script",
    description="Generate a Python script for custom network analysis",
    params={
        "analysis_description": {"type": "string"}
    }
)
async def create_analysis_script(args):
    description = args["analysis_description"]

    # Have Claude generate the script
    script = await generate_script_with_claude(description)

    # Save to file
    script_path = f"/tmp/analysis_{uuid.uuid4()}.py"
    with open(script_path, "w") as f:
        f.write(script)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Created script at {script_path}. Use the 'run_script' tool to execute it."
            }
        ]
    }

@tool("run_script", "Execute a generated analysis script")
async def run_script(args):
    script_path = args["script_path"]
    result = subprocess.run(["python", script_path], capture_output=True)
    return {"content": [{"type": "text", "text": result.stdout.decode()}]}
```

### 4.6 External MCP Servers

For database integrations, you can use external MCP servers:

```python
# .mcp.json configuration
{
  "neo4j": {
    "command": "npx",
    "args": ["-y", "@neo4j/mcp-server-neo4j"],
    "env": {
      "NEO4J_URI": "bolt://localhost:7687",
      "NEO4J_USERNAME": "neo4j",
      "NEO4J_PASSWORD": "password"
    }
  }
}
```

Then use in agent:

```python
options = ClaudeAgentOptions(
    mcp_config_path=".mcp.json",
    allowed_tools=["mcp__neo4j__read-neo4j-cypher"]
)
```

---

## 5. User Interaction Patterns

### 5.1 How Agents Ask for Clarification

The agent loop naturally supports clarification requests:

```python
# Agent's perspective (simplified)
async def agent_task(goal):
    # Agent analyzes the goal
    if "ambiguous query" in goal:
        # Agent outputs text asking for clarification
        # NO TOOL CALL - loop stops and waits for user
        return "I need clarification: are you asking about X or Y?"
    else:
        # Agent calls tools to accomplish goal
        use_tool("query_graph", params)
```

**Pattern in Practice:**

```python
async with ClaudeSDKClient() as client:
    # User's vague request
    await client.query("Find important papers")

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
                    # Claude might say: "I need clarification. By 'important',
                    # do you mean: (1) most cited, (2) most recent, or
                    # (3) most relevant to a specific topic?"

    # User provides clarification
    user_response = input("You: ")
    await client.query(user_response)

    # Agent continues with clearer goal
    async for message in client.receive_response():
        # Agent now calls appropriate tools
        pass
```

### 5.2 Multi-Turn Conversations

ClaudeSDKClient maintains context across turns:

```python
async def interactive_network_analysis():
    async with ClaudeSDKClient(options=network_science_options) as client:
        print("Network Science Expert Agent Ready")

        while True:
            # Get user input
            user_query = input("\nYou: ")
            if user_query.lower() in ["exit", "quit"]:
                break

            # Send to agent
            await client.query(user_query)

            # Process agent's response
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"\nAgent: {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"[Using tool: {block.name}]")

                elif isinstance(message, ToolResultMessage):
                    # Tool results are fed back to agent automatically
                    pass
```

### 5.3 Interrupting the Agent

You can interrupt by implementing a cancel mechanism:

```python
import asyncio
import signal

async def interruptible_agent():
    client = ClaudeSDKClient(options=options)

    # Set up signal handler for Ctrl+C
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        print("\n[Interrupting agent...]")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    async with client:
        await client.query("Long-running analysis task")

        async for message in client.receive_response():
            # Check for interrupt
            if stop_event.is_set():
                print("Agent interrupted by user")
                break

            # Process message
            handle_message(message)
```

### 5.4 Terminal UX Best Practices

**Rich Terminal Output:**

```python
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live

console = Console()

async def rich_terminal_ux():
    async with ClaudeSDKClient(options=options) as client:
        console.print(Panel.fit(
            "[bold cyan]Network Science Expert Agent[/bold cyan]\n"
            "Ask me anything about network analysis, graph theory, or centrality metrics.",
            title="🔬 Agent Ready"
        ))

        while True:
            user_input = console.input("\n[bold green]You:[/bold green] ")

            if user_input.lower() in ["exit", "quit"]:
                break

            await client.query(user_input)

            console.print("\n[bold blue]Agent:[/bold blue]")

            full_response = ""
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text
                        elif isinstance(block, ToolUseBlock):
                            console.print(f"[dim]⚙️  Using tool: {block.name}[/dim]")

            # Render as markdown
            console.print(Markdown(full_response))
```

**Progress Indicators:**

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

async def agent_with_progress():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:

        task = progress.add_task("Agent thinking...", total=None)

        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_query)

            async for message in client.receive_response():
                if isinstance(message, ToolUseBlock):
                    progress.update(task, description=f"Using {message.name}...")

        progress.stop()
```

---

## 6. Advanced Agent Patterns

### 6.1 Sub-Agents & Delegation

Sub-agents enable:
1. **Parallelization**: Multiple agents work on different tasks simultaneously
2. **Context Isolation**: Each sub-agent has its own context window
3. **Specialization**: Dedicated agents for specific domains

**Architecture:**

```
┌─────────────────────────────────┐
│   Orchestrator Agent            │
│   - Global planning             │
│   - Task delegation             │
│   - State management            │
└──────────┬──────────────────────┘
           │
           ├──────────┬──────────────┬──────────────┐
           │          │              │              │
      ┌────▼───┐ ┌────▼───┐   ┌─────▼────┐  ┌──────▼─────┐
      │SubAgent│ │SubAgent│   │SubAgent  │  │SubAgent    │
      │ Graph  │ │Compute │   │Visualize │  │Summarize   │
      │ Query  │ │Metrics │   │Results   │  │Findings    │
      └────────┘ └────────┘   └──────────┘  └────────────┘
```

**Implementation Pattern:**

```python
# Create specialized sub-agents via .claude/agents/

# .claude/agents/graph-query-expert.md
"""
---
name: graph-query-expert
description: Expert in querying knowledge graphs with Cypher
tools: ["mcp__graph__query_cypher"]
---

You are an expert in querying knowledge graphs using Cypher.

Your role:
1. Translate natural language questions into optimized Cypher queries
2. Execute queries against the knowledge graph
3. Return structured results

When given a question:
- Analyze what graph patterns are needed
- Write an efficient Cypher query
- Execute and verify results
- Return findings to orchestrator
"""

# .claude/agents/network-metrics-expert.md
"""
---
name: network-metrics-expert
description: Expert in calculating network science metrics
tools: ["mcp__graph__calculate_centrality", "mcp__graph__community_detection"]
---

You are an expert in network science metrics and analysis.

Your role:
1. Calculate centrality measures (degree, betweenness, closeness, eigenvector)
2. Detect communities using various algorithms
3. Compute network statistics

When given a network analysis task:
- Determine appropriate metrics
- Run calculations
- Interpret results in network science context
- Return analysis to orchestrator
"""
```

**Orchestrator Pattern:**

```python
async def orchestrator_agent(user_question: str):
    """
    Main orchestrator that delegates to specialized sub-agents.
    """
    async with ClaudeSDKClient(options=orchestrator_options) as client:
        # Give orchestrator access to sub-agent delegation
        orchestrator_prompt = f"""
You are the Network Science Orchestrator. You coordinate specialized sub-agents to answer complex network science questions.

Available sub-agents:
- graph-query-expert: For querying the knowledge graph
- network-metrics-expert: For calculating network metrics
- visualization-expert: For creating visualizations
- summarization-expert: For synthesizing findings

User question: {user_question}

Plan your approach:
1. Break down the question into sub-tasks
2. Delegate to appropriate sub-agents
3. Synthesize results
4. Provide comprehensive answer
"""

        await client.query(orchestrator_prompt)

        # Orchestrator can invoke sub-agents via tools
        async for message in client.receive_response():
            handle_orchestrator_message(message)
```

### 6.2 Planning and Reflection

**Explicit Planning Pattern:**

```python
async def agent_with_planning(goal: str):
    async with ClaudeSDKClient() as client:
        # Phase 1: Planning
        planning_prompt = f"""
Goal: {goal}

Before taking action, create a detailed plan:

1. Break down the goal into specific sub-tasks
2. Identify what information you need
3. Determine which tools are required
4. Establish success criteria
5. Anticipate potential issues

Output your plan as a numbered list, then I'll confirm before you proceed.
"""

        await client.query(planning_prompt)

        plan = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        plan = block.text
                        print(f"Agent's Plan:\n{plan}")

        # User can review and approve plan
        approval = input("\nApprove plan? (yes/no): ")

        if approval.lower() == "yes":
            # Phase 2: Execution with reflection
            execution_prompt = """
Execute your plan. After each step:
1. Verify the results
2. Check if they meet expectations
3. Reflect on whether to continue or adjust
4. Proceed or replan as needed
"""
            await client.query(execution_prompt)

            async for message in client.receive_response():
                handle_execution_message(message)
```

**Self-Reflection Pattern:**

```python
@tool(
    name="verify_results",
    description="Verify that results meet quality criteria",
    params={
        "results": {"type": "string"},
        "criteria": {"type": "string"}
    }
)
async def verify_results(args):
    """
    Tool that forces the agent to explicitly verify its work.
    """
    results = args["results"]
    criteria = args["criteria"]

    # You could use another LLM call here for verification
    # Or use rule-based checks

    verification_prompt = f"""
Evaluate these results against the criteria:

Results: {results}

Criteria: {criteria}

Assessment:
- Do results fully satisfy criteria? (Yes/No)
- What's missing or incorrect?
- What should be improved?
- Next steps?
"""

    # This creates a reflection step
    return {"content": [{"type": "text", "text": verification_prompt}]}
```

### 6.3 Expert Agent Specialization

**Creating a Network Science Expert:**

```python
# System prompt engineering for expertise
NETWORK_SCIENCE_EXPERT_PROMPT = """
You are a world-class network science expert with deep knowledge of:

**Graph Theory:**
- Graph representations (adjacency matrix, edge lists, adjacency lists)
- Graph types (directed, undirected, weighted, bipartite, multigraph)
- Graph properties (diameter, density, clustering coefficient)

**Centrality Measures:**
- Degree centrality (in-degree, out-degree)
- Betweenness centrality (node and edge)
- Closeness centrality
- Eigenvector centrality
- PageRank
- Katz centrality

**Community Detection:**
- Modularity optimization (Louvain, Leiden)
- Label propagation
- Girvan-Newman algorithm
- Spectral clustering
- Clique percolation

**Network Models:**
- Erdős-Rényi random graphs
- Watts-Strogatz small-world networks
- Barabási-Albert scale-free networks
- Configuration model
- Stochastic block models

**Applications:**
- Social network analysis
- Biological networks (protein interaction, gene regulatory)
- Infrastructure networks (transportation, power grids)
- Information networks (citation networks, knowledge graphs)

When analyzing networks:
1. Start by understanding network structure and properties
2. Choose appropriate metrics based on research question
3. Consider both local (node-level) and global (network-level) measures
4. Interpret results in domain context
5. Visualize findings when helpful

You have access to tools for querying knowledge graphs and calculating network metrics. Use them judiciously to provide thorough, accurate answers grounded in network science theory.
"""

async def create_network_science_expert():
    options = ClaudeAgentOptions(
        system_prompt=NETWORK_SCIENCE_EXPERT_PROMPT,
        mcp_servers={"graph": graph_tools},
        allowed_tools=[
            "mcp__graph__query_cypher",
            "mcp__graph__calculate_centrality",
            "mcp__graph__community_detection",
            "mcp__graph__compute_network_stats"
        ]
    )

    return ClaudeSDKClient(options=options)
```

### 6.4 Autonomy vs Reactive

**Levels of Autonomy:**

```
┌────────────────────────────────────────────────────────┐
│ Level 0: No Autonomy (Pure Reactive)                   │
│ - Answers single question                              │
│ - No tool use                                           │
│ - No iteration                                          │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│ Level 1: Tool Use (Reactive with Capabilities)         │
│ - Uses tools to answer questions                       │
│ - No planning or verification                           │
│ - Single-pass execution                                 │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│ Level 2: Iterative (Self-Correcting)                   │
│ - Uses tools                                            │
│ - Verifies results                                      │
│ - Retries on failure                                    │
│ - Still reactive to user prompts                        │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│ Level 3: Goal-Oriented (Semi-Autonomous)               │
│ - Plans multi-step approach                             │
│ - Breaks down goals                                     │
│ - Self-corrects and adapts                              │
│ - Asks for clarification when needed                    │
│ - Still requires user to initiate tasks                 │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│ Level 4: Fully Autonomous (Proactive)                  │
│ - Identifies goals from context                         │
│ - Self-initiates tasks                                  │
│ - Manages long-running workflows                        │
│ - Schedules periodic checks                             │
│ - Reports back proactively                              │
└────────────────────────────────────────────────────────┘
```

**Implementing Level 3 (Recommended for most cases):**

```python
async def goal_oriented_agent(goal: str):
    """
    Agent that demonstrates Level 3 autonomy:
    - Plans approach
    - Self-corrects
    - Asks for clarification
    - Verifies completion
    """
    async with ClaudeSDKClient(options=options) as client:
        enhanced_prompt = f"""
Goal: {goal}

You are a goal-oriented agent. Your process:

1. UNDERSTAND: Analyze the goal. If ambiguous, ask for clarification.
2. PLAN: Break down into sub-tasks with success criteria.
3. EXECUTE: Use tools to complete sub-tasks.
4. VERIFY: Check if each sub-task meets success criteria.
5. ADAPT: If verification fails, adjust approach and retry.
6. COMPLETE: When all success criteria met, report completion.

At each step, explicitly state:
- What you're doing and why
- What you expect to learn/achieve
- What you'll verify

Begin by analyzing the goal.
"""

        await client.query(enhanced_prompt)

        async for message in client.receive_response():
            # Agent autonomously manages the workflow
            handle_agent_message(message)
```

---

## 7. State and Memory Management

### 7.1 Short-Term Memory (Session Context)

ClaudeSDKClient automatically maintains conversation context:

```python
async with ClaudeSDKClient() as client:
    # Turn 1
    await client.query("Analyze the social network in data/network.graphml")
    async for msg in client.receive_response():
        pass  # Agent analyzes network

    # Turn 2 - Agent remembers previous analysis
    await client.query("Now compute betweenness centrality for the top 5 nodes")
    async for msg in client.receive_response():
        pass  # Agent knows which network and which top 5 nodes

    # Turn 3 - Agent still has context
    await client.query("Compare these to the degree centrality we discussed")
    async for msg in client.receive_response():
        pass  # Agent remembers degree centrality from Turn 1
```

### 7.2 Context Compaction

To prevent context overflow, the SDK automatically compacts:

**What gets compressed:**
- Older conversation turns
- Raw tool outputs
- Redundant information

**What stays:**
- Recent messages
- Key decisions
- Active tasks
- User preferences

**Manual compaction pattern:**

```python
async def managed_context_agent():
    async with ClaudeSDKClient() as client:
        for i, query in enumerate(long_query_list):
            await client.query(query)

            async for msg in client.receive_response():
                handle_message(msg)

            # Every 10 queries, explicitly summarize context
            if i % 10 == 9:
                await client.query("""
Summarize the key findings from our last 10 interactions into a concise bullet list.
This will be our working memory going forward.
""")
                async for msg in client.receive_response():
                    save_summary(msg)
```

### 7.3 Long-Term Memory (CLAUDE.md)

**Project Memory:**

Create `.claude/CLAUDE.md` in your project:

```markdown
# Network Science Knowledge Graph Project

## Project Context
This is a knowledge graph of research papers in network science, covering:
- ~50,000 papers from 2000-2024
- Citation network
- Author collaboration network
- Topic/keyword associations

## Database Schema
The Neo4j graph has the following node types:
- Paper (properties: id, title, year, abstract, doi)
- Author (properties: id, name, affiliation)
- Topic (properties: id, name, category)

Relationship types:
- CITES (Paper → Paper)
- AUTHORED_BY (Paper → Author)
- COLLABORATES_WITH (Author → Author, derived)
- ABOUT (Paper → Topic)

## User Preferences
- User prefers visualizations for network metrics
- User is interested in community detection in citation networks
- User's research focus: information diffusion in social networks

## Key Findings (Updated as we work)
- The citation network has small-world properties (avg path length: 4.3)
- Three major research communities identified: social networks, biological networks, and infrastructure networks
- Most influential paper: "Network Science" by Barabási (betweenness centrality: 0.234)
```

The agent automatically reads this file and incorporates it into its context.

### 7.4 Memory Tools Pattern

Create explicit memory management tools:

```python
@tool(
    name="save_to_memory",
    description="Save important information to long-term memory",
    params={
        "key": {"type": "string", "description": "Memory key (e.g., 'user_preferences', 'key_findings')"},
        "content": {"type": "string", "description": "Content to save"}
    }
)
async def save_to_memory(args):
    key = args["key"]
    content = args["content"]

    # Persist to database or file
    memory_store[key] = {
        "content": content,
        "timestamp": datetime.now().isoformat()
    }

    return {"content": [{"type": "text", "text": f"Saved to memory: {key}"}]}

@tool(
    name="recall_from_memory",
    description="Retrieve information from long-term memory",
    params={
        "key": {"type": "string", "description": "Memory key to retrieve"}
    }
)
async def recall_from_memory(args):
    key = args["key"]

    if key in memory_store:
        memory = memory_store[key]
        return {
            "content": [{
                "type": "text",
                "text": f"Memory '{key}' (from {memory['timestamp']}):\n{memory['content']}"
            }]
        }
    else:
        return {"content": [{"type": "text", "text": f"No memory found for key: {key}"}]}
```

**Agent uses memory:**

```
Agent: "Let me recall what we've learned about this network..."
[Uses recall_from_memory tool with key="network_properties"]

Agent: "Based on our previous findings (degree distribution is power-law),
I'll now calculate betweenness centrality for hub nodes..."

[Later]
Agent: "I should save this important finding for future reference."
[Uses save_to_memory tool with key="key_findings" and content="..."]
```

### 7.5 State Management for Long-Running Tasks

```python
class NetworkAnalysisAgent:
    def __init__(self):
        self.state = {
            "current_task": None,
            "completed_tasks": [],
            "pending_tasks": [],
            "findings": {},
            "current_graph": None
        }
        self.client = None

    async def start(self):
        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()

    async def execute_task(self, task: str):
        self.state["current_task"] = task

        # Include state in prompt
        state_context = f"""
Current State:
- Task: {task}
- Completed: {self.state['completed_tasks']}
- Findings so far: {json.dumps(self.state['findings'], indent=2)}

Execute this task and update findings as needed.
"""

        await self.client.query(state_context)

        async for message in self.client.receive_response():
            # Update state based on agent actions
            await self.update_state(message)

    async def update_state(self, message):
        # Parse agent's response and update state
        if "task complete" in str(message).lower():
            self.state["completed_tasks"].append(self.state["current_task"])
            self.state["current_task"] = None

        # Extract findings from agent response
        # ... (parse and update state['findings'])
```

---

## 8. Code Examples

### 8.1 Complete Agent: Network Science Expert

```python
#!/usr/bin/env python3
"""
Network Science Expert Agent

A goal-oriented agent that can:
- Answer questions about network science
- Query a knowledge graph of research papers
- Calculate network metrics
- Explain concepts and provide visualizations
- Maintain conversation context
"""

import asyncio
import json
from typing import Optional
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    ToolUseBlock
)
from neo4j import AsyncGraphDatabase
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Initialize Rich console for pretty output
console = Console()

# ============================================================================
# TOOLS
# ============================================================================

@tool(
    name="query_knowledge_graph",
    description="""
    Query the research paper knowledge graph using Cypher.

    The graph contains:
    - Paper nodes (properties: id, title, year, abstract)
    - Author nodes (properties: id, name)
    - Topic nodes (properties: id, name)
    - CITES relationships (paper citations)
    - AUTHORED_BY relationships
    - ABOUT relationships (paper topics)

    Use this to find papers, explore citations, analyze authors, etc.
    """,
    params={
        "query": {
            "type": "string",
            "description": "Cypher query to execute"
        },
        "explain": {
            "type": "boolean",
            "description": "If true, explain the query logic",
            "default": False
        }
    }
)
async def query_knowledge_graph(args):
    query = args["query"]
    explain = args.get("explain", False)

    # Connect to Neo4j (in real implementation, use connection pool)
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password")
    )

    try:
        async with driver.session() as session:
            result = await session.run(query)
            records = await result.data()

        output = f"Query returned {len(records)} results.\n\n"

        if explain:
            output += f"Query: {query}\n\n"

        output += "Results:\n"
        output += json.dumps(records[:10], indent=2)  # Limit to 10 for context

        if len(records) > 10:
            output += f"\n\n... and {len(records) - 10} more results"

        return {"content": [{"type": "text", "text": output}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error executing query: {str(e)}"}]}

    finally:
        await driver.close()


@tool(
    name="calculate_network_metrics",
    description="""
    Calculate network science metrics and statistics.

    Available metrics:
    - degree_centrality: Importance based on number of connections
    - betweenness_centrality: Importance based on bridging paths
    - closeness_centrality: Importance based on proximity to all nodes
    - eigenvector_centrality: Importance based on connections to important nodes
    - pagerank: Google's algorithm for node importance
    - clustering_coefficient: Measure of local clustering
    - degree_distribution: Distribution of node degrees
    """,
    params={
        "metric": {
            "type": "string",
            "enum": [
                "degree_centrality",
                "betweenness_centrality",
                "closeness_centrality",
                "eigenvector_centrality",
                "pagerank",
                "clustering_coefficient",
                "degree_distribution"
            ],
            "description": "The metric to calculate"
        },
        "node_ids": {
            "type": "array",
            "description": "Optional: specific node IDs to analyze (if empty, analyzes all)",
            "items": {"type": "string"},
            "default": []
        },
        "top_k": {
            "type": "number",
            "description": "Return top K nodes by this metric",
            "default": 10
        }
    }
)
async def calculate_network_metrics(args):
    metric = args["metric"]
    node_ids = args.get("node_ids", [])
    top_k = args.get("top_k", 10)

    # In real implementation, use NetworkX or graph algorithms
    # This is a simplified example

    results = {
        "metric": metric,
        "top_nodes": [
            {"node_id": f"paper_{i}", "score": 0.9 - i*0.05}
            for i in range(top_k)
        ],
        "statistics": {
            "mean": 0.45,
            "median": 0.42,
            "std": 0.18
        }
    }

    output = f"Calculated {metric} for the network.\n\n"
    output += f"Top {top_k} nodes:\n"
    for item in results["top_nodes"]:
        output += f"  - {item['node_id']}: {item['score']:.3f}\n"

    output += f"\nStatistics:\n"
    output += f"  Mean: {results['statistics']['mean']:.3f}\n"
    output += f"  Median: {results['statistics']['median']:.3f}\n"
    output += f"  Std Dev: {results['statistics']['std']:.3f}\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    name="detect_communities",
    description="""
    Detect communities/clusters in the network using various algorithms.

    Algorithms:
    - louvain: Fast modularity optimization (good for large networks)
    - leiden: Improved Louvain algorithm
    - label_propagation: Fast, good for large networks
    - girvan_newman: Edge betweenness-based (slow, accurate)
    """,
    params={
        "algorithm": {
            "type": "string",
            "enum": ["louvain", "leiden", "label_propagation", "girvan_newman"],
            "description": "Community detection algorithm"
        },
        "min_community_size": {
            "type": "number",
            "description": "Minimum size of communities to report",
            "default": 5
        }
    }
)
async def detect_communities(args):
    algorithm = args["algorithm"]
    min_size = args.get("min_community_size", 5)

    # Simplified mock results
    communities = [
        {
            "community_id": 0,
            "size": 1234,
            "description": "Social Network Analysis",
            "top_papers": ["paper_1", "paper_45", "paper_89"]
        },
        {
            "community_id": 1,
            "size": 987,
            "description": "Biological Networks",
            "top_papers": ["paper_23", "paper_56", "paper_91"]
        },
        {
            "community_id": 2,
            "size": 756,
            "description": "Infrastructure Networks",
            "top_papers": ["paper_12", "paper_67", "paper_103"]
        }
    ]

    output = f"Detected {len(communities)} communities using {algorithm} algorithm.\n\n"

    for comm in communities:
        output += f"Community {comm['community_id']} ({comm['size']} papers):\n"
        output += f"  Theme: {comm['description']}\n"
        output += f"  Top papers: {', '.join(comm['top_papers'])}\n\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    name="explain_concept",
    description="""
    Provide a detailed explanation of a network science concept with examples.
    Use this when the user asks 'what is' or 'explain' something.
    """,
    params={
        "concept": {
            "type": "string",
            "description": "The network science concept to explain"
        }
    }
)
async def explain_concept(args):
    concept = args["concept"]

    # In a real implementation, this could query a database of explanations
    # or use a specialized knowledge base

    return {
        "content": [{
            "type": "text",
            "text": f"""I'll provide a detailed explanation of {concept}.

Note: For the most accurate and comprehensive explanation, I should use my
network science expertise combined with specific examples from the knowledge graph.
Let me analyze the concept: {concept}"""
        }]
    }

# ============================================================================
# NETWORK SCIENCE EXPERT SYSTEM PROMPT
# ============================================================================

NETWORK_SCIENCE_EXPERT_PROMPT = """
You are a world-renowned network science expert with deep expertise in graph theory,
social network analysis, complex systems, and computational methods.

## Your Expertise Areas:

**Core Network Science:**
- Graph theory and representations
- Centrality measures (degree, betweenness, closeness, eigenvector, PageRank, Katz)
- Community detection and modularity
- Network models (random, small-world, scale-free, stochastic block models)
- Network dynamics and evolution
- Diffusion and spreading processes

**Applications:**
- Social network analysis
- Biological networks (protein interaction, gene regulatory, metabolic)
- Infrastructure networks (transportation, power grids, internet)
- Knowledge graphs and citation networks
- Organizational networks

**Methods:**
- Graph algorithms and complexity
- Statistical network analysis
- Network visualization
- Machine learning on graphs
- Temporal and multilayer networks

## Your Approach:

When a user asks a question:

1. **Understand the Question**
   - Identify if it's about concepts, data analysis, or both
   - If ambiguous, ask clarifying questions
   - Consider the user's level of expertise

2. **Plan Your Analysis**
   - Determine what information you need from the knowledge graph
   - Decide which metrics or algorithms are appropriate
   - Consider multiple approaches if relevant

3. **Execute with Tools**
   - Query the knowledge graph for relevant papers/data
   - Calculate metrics using network analysis tools
   - Detect communities or patterns if needed

4. **Interpret Results**
   - Explain findings in network science context
   - Connect to theoretical concepts
   - Provide intuition and examples
   - Suggest follow-up analyses if appropriate

5. **Communicate Clearly**
   - Use precise technical language when appropriate
   - Provide intuitive explanations for complex concepts
   - Include relevant citations from the knowledge graph
   - Visualize when it helps understanding

## Available Tools:

- **query_knowledge_graph**: Query the research paper knowledge graph (Neo4j/Cypher)
- **calculate_network_metrics**: Compute centrality, clustering, degree distributions
- **detect_communities**: Run community detection algorithms
- **explain_concept**: Provide detailed explanations of concepts

## Style:

- Be thorough but concise
- Ground answers in network science theory
- Cite specific papers from the knowledge graph when relevant
- Acknowledge uncertainty or limitations
- Suggest further reading or analysis
- Use analogies and examples to clarify complex concepts

You are helpful, rigorous, and deeply knowledgeable. You aim to educate while
providing accurate, actionable insights.
"""

# ============================================================================
# MAIN AGENT
# ============================================================================

async def main():
    """Main function to run the Network Science Expert Agent."""

    # Create MCP server with our tools
    network_tools = create_sdk_mcp_server(
        name="network-science-tools",
        version="1.0.0",
        tools=[
            query_knowledge_graph,
            calculate_network_metrics,
            detect_communities,
            explain_concept
        ]
    )

    # Configure agent options
    options = ClaudeAgentOptions(
        system_prompt=NETWORK_SCIENCE_EXPERT_PROMPT,
        mcp_servers={"nettools": network_tools},
        allowed_tools=[
            "mcp__nettools__query_knowledge_graph",
            "mcp__nettools__calculate_network_metrics",
            "mcp__nettools__detect_communities",
            "mcp__nettools__explain_concept"
        ]
    )

    # Display welcome message
    console.print(Panel.fit(
        "[bold cyan]Network Science Expert Agent[/bold cyan]\n\n"
        "I'm an expert in network science, graph theory, and complex systems.\n"
        "I can help you:\n"
        "  • Query the research paper knowledge graph\n"
        "  • Calculate network metrics (centrality, clustering, etc.)\n"
        "  • Detect communities in networks\n"
        "  • Explain network science concepts\n"
        "  • Analyze citation patterns and research trends\n\n"
        "[dim]Type 'exit' or 'quit' to end the session.[/dim]",
        title="🔬 Welcome",
        border_style="cyan"
    ))

    # Start agent client
    async with ClaudeSDKClient(options=options) as client:

        while True:
            # Get user input
            console.print()
            user_input = console.input("[bold green]You:[/bold green] ")

            # Check for exit
            if user_input.lower().strip() in ["exit", "quit", "bye"]:
                console.print("\n[cyan]Thank you for using Network Science Expert Agent![/cyan]")
                break

            if not user_input.strip():
                continue

            # Send query to agent
            await client.query(user_input)

            console.print("\n[bold blue]Agent:[/bold blue]")

            # Collect response
            full_response = ""
            tool_uses = []

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append(block.name)
                            console.print(f"[dim]  ⚙️  Using tool: {block.name}[/dim]")

            # Display response as markdown
            if full_response:
                console.print(Markdown(full_response))

            # Show tool summary if multiple tools were used
            if len(tool_uses) > 1:
                console.print(f"\n[dim]Tools used: {', '.join(set(tool_uses))}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
```

### 8.2 Example: Simple Query

```python
#!/usr/bin/env python3
"""
Simple example of using the Claude Agent SDK.
"""

import asyncio
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock

async def simple_query():
    async with ClaudeSDKClient() as client:
        # Ask a question
        await client.query("What is betweenness centrality in network science?")

        # Get response
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)

if __name__ == "__main__":
    asyncio.run(simple_query())
```

### 8.3 Example: Hooks for Safety

```python
#!/usr/bin/env python3
"""
Example of using hooks to enforce safety policies.
"""

import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    PreToolUse,
    ToolUseBlock
)

async def check_dangerous_query(context, hook_input):
    """
    Hook to prevent execution of dangerous Cypher queries.
    """
    tool_input = hook_input.input

    if "query" in tool_input:
        query = tool_input["query"].lower()

        # Block destructive operations
        dangerous_keywords = ["delete", "drop", "remove", "detach", "create"]

        for keyword in dangerous_keywords:
            if keyword in query:
                return {
                    "permission": "deny",
                    "reason": f"Query contains potentially destructive operation: {keyword.upper()}"
                }

    # Allow by default
    return {"permission": "allow"}


async def main():
    # Set up hooks
    hooks = [
        HookMatcher(
            patterns=[PreToolUse(tool_name="query_knowledge_graph")],
            handler=check_dangerous_query
        )
    ]

    options = ClaudeAgentOptions(
        hooks=hooks
        # ... other options
    )

    async with ClaudeSDKClient(options=options) as client:
        # This would be blocked by the hook
        await client.query("Delete all papers from the graph")

        async for message in client.receive_response():
            print(message)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Building a Network Science Expert Agent

### 9.1 Architecture for Your Use Case

Based on your requirements, here's the recommended architecture:

```
┌───────────────────────────────────────────────────────────────┐
│                        USER (Terminal)                         │
│                    Natural language questions                  │
└────────────────────────────┬──────────────────────────────────┘
                             │
┌────────────────────────────▼──────────────────────────────────┐
│               Network Science Expert Agent                     │
│                   (ClaudeSDKClient)                            │
│                                                                 │
│  System Prompt: Network science expertise                      │
│  Model: Claude Sonnet 4.5 (extended thinking)                 │
│  Context: CLAUDE.md with domain knowledge                      │
└──────┬─────────────────────────────────────────────┬──────────┘
       │                                             │
       │  Tool Calls                                 │  Clarification
       │                                             │  Questions
       ▼                                             ▼
┌──────────────────────────────────────────────────────────────┐
│                      MCP Tools                                │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Knowledge Graph Tools:                                   │
│     • query_knowledge_graph (Cypher queries)                 │
│     • get_paper_details                                      │
│     • get_citation_network                                   │
│     • search_papers                                          │
│                                                               │
│  📈 Network Metrics Tools:                                   │
│     • calculate_centrality                                   │
│     • compute_clustering                                     │
│     • analyze_degree_distribution                            │
│     • calculate_shortest_paths                               │
│                                                               │
│  🔍 Analysis Tools:                                          │
│     • detect_communities                                     │
│     • identify_influential_papers                            │
│     • analyze_research_trends                                │
│     • compare_networks                                       │
│                                                               │
│  💾 Memory Tools:                                            │
│     • save_finding                                           │
│     • recall_context                                         │
│     • update_user_preferences                                │
│                                                               │
└──────────┬───────────────────────────────────┬───────────────┘
           │                                   │
           ▼                                   ▼
    ┌─────────────┐                    ┌─────────────┐
    │   Neo4j     │                    │  NetworkX   │
    │ Knowledge   │                    │  Analysis   │
    │   Graph     │                    │   Engine    │
    └─────────────┘                    └─────────────┘
```

### 9.2 Step-by-Step Implementation

#### Step 1: Set Up Environment

```bash
# Install dependencies
pip install claude-agent-sdk
pip install neo4j
pip install networkx
pip install rich  # For pretty terminal output

# Ensure Claude Code is installed
npm install -g @anthropic/claude-code

# Create project structure
mkdir network-science-agent
cd network-science-agent
mkdir -p .claude/agents
```

#### Step 2: Create Domain Knowledge File

`.claude/CLAUDE.md`:

```markdown
# Network Science Expert Agent Context

## Knowledge Graph Schema

Our Neo4j knowledge graph contains:

### Nodes:
- **Paper**: Research papers (properties: id, title, abstract, year, doi)
- **Author**: Researchers (properties: id, name, affiliation)
- **Topic**: Research topics (properties: id, name, category)
- **Venue**: Publication venues (properties: id, name, type)

### Relationships:
- **CITES**: Paper → Paper (citation relationships)
- **AUTHORED_BY**: Paper → Author
- **ABOUT**: Paper → Topic
- **PUBLISHED_IN**: Paper → Venue
- **COLLABORATES_WITH**: Author → Author (inferred from co-authorship)

## Network Properties

Based on initial analysis:
- ~50,000 papers (2000-2024)
- ~25,000 unique authors
- Citation network has small-world properties
- Average path length: 4.3
- Clustering coefficient: 0.21
- Power-law degree distribution (scale-free)

## User Context

- Researcher in network science
- Interested in information diffusion and social networks
- Prefers technical explanations with mathematical rigor
- Values visualizations and empirical evidence

## Common Queries

The user frequently asks about:
1. Centrality measures and their interpretations
2. Community structure in citation networks
3. Research trends over time
4. Influential papers and authors
```

#### Step 3: Implement Tools

`tools/graph_tools.py`:

```python
from claude_agent_sdk import tool
from neo4j import AsyncGraphDatabase
import json

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"

@tool(
    name="query_knowledge_graph",
    description="Query the research paper knowledge graph using Cypher queries",
    params={
        "query": {"type": "string", "description": "Cypher query to execute"},
        "limit": {"type": "number", "description": "Max results to return", "default": 20}
    }
)
async def query_knowledge_graph(args):
    query = args["query"]
    limit = args.get("limit", 20)

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit}"

            result = await session.run(query)
            records = await result.data()

        return {
            "content": [{
                "type": "text",
                "text": f"Query returned {len(records)} results:\n\n" +
                        json.dumps(records, indent=2)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error executing query: {str(e)}\n\nPlease check Cypher syntax."
            }]
        }

    finally:
        await driver.close()


@tool(
    name="find_papers_by_topic",
    description="Find research papers about a specific topic or keyword",
    params={
        "topic": {"type": "string", "description": "Topic or keyword to search for"},
        "year_start": {"type": "number", "description": "Earliest year (optional)"},
        "year_end": {"type": "number", "description": "Latest year (optional)"},
        "limit": {"type": "number", "description": "Max results", "default": 10}
    }
)
async def find_papers_by_topic(args):
    topic = args["topic"]
    year_start = args.get("year_start")
    year_end = args.get("year_end")
    limit = args.get("limit", 10)

    # Build Cypher query
    query = f"""
    MATCH (p:Paper)-[:ABOUT]->(t:Topic)
    WHERE toLower(t.name) CONTAINS toLower('{topic}')
       OR toLower(p.title) CONTAINS toLower('{topic}')
       OR toLower(p.abstract) CONTAINS toLower('{topic}')
    """

    if year_start:
        query += f" AND p.year >= {year_start}"
    if year_end:
        query += f" AND p.year <= {year_end}"

    query += f"""
    RETURN p.id as id, p.title as title, p.year as year, t.name as topic
    ORDER BY p.year DESC
    LIMIT {limit}
    """

    # Reuse query_knowledge_graph
    return await query_knowledge_graph({"query": query, "limit": limit})
```

`tools/network_tools.py`:

```python
from claude_agent_sdk import tool
import networkx as nx
from neo4j import AsyncGraphDatabase
import json

@tool(
    name="calculate_centrality",
    description="Calculate centrality metrics for nodes in the citation network",
    params={
        "metric": {
            "type": "string",
            "enum": ["degree", "betweenness", "closeness", "eigenvector", "pagerank"],
            "description": "Centrality metric to calculate"
        },
        "node_type": {
            "type": "string",
            "enum": ["paper", "author"],
            "description": "Type of nodes to analyze",
            "default": "paper"
        },
        "top_k": {
            "type": "number",
            "description": "Return top K most central nodes",
            "default": 10
        }
    }
)
async def calculate_centrality(args):
    metric = args["metric"]
    node_type = args.get("node_type", "paper")
    top_k = args.get("top_k", 10)

    # Fetch network from Neo4j
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # Get edges
            if node_type == "paper":
                query = "MATCH (p1:Paper)-[:CITES]->(p2:Paper) RETURN p1.id as source, p2.id as target"
            else:  # author
                query = "MATCH (a1:Author)-[:COLLABORATES_WITH]->(a2:Author) RETURN a1.id as source, a2.id as target"

            result = await session.run(query)
            edges = await result.data()

        # Build NetworkX graph
        G = nx.DiGraph()
        for edge in edges:
            G.add_edge(edge["source"], edge["target"])

        # Calculate centrality
        if metric == "degree":
            centrality = nx.degree_centrality(G)
        elif metric == "betweenness":
            centrality = nx.betweenness_centrality(G)
        elif metric == "closeness":
            centrality = nx.closeness_centrality(G)
        elif metric == "eigenvector":
            centrality = nx.eigenvector_centrality(G, max_iter=1000)
        elif metric == "pagerank":
            centrality = nx.pagerank(G)

        # Get top K
        top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch node details
        node_ids = [node[0] for node in top_nodes]
        async with driver.session() as session:
            if node_type == "paper":
                details_query = f"""
                MATCH (p:Paper)
                WHERE p.id IN {node_ids}
                RETURN p.id as id, p.title as title, p.year as year
                """
            else:
                details_query = f"""
                MATCH (a:Author)
                WHERE a.id IN {node_ids}
                RETURN a.id as id, a.name as name, a.affiliation as affiliation
                """

            result = await session.run(details_query)
            details = {item["id"]: item for item in await result.data()}

        # Format output
        output = f"Top {top_k} {node_type}s by {metric} centrality:\n\n"

        for node_id, score in top_nodes:
            detail = details.get(node_id, {})
            if node_type == "paper":
                output += f"• {detail.get('title', node_id)} ({detail.get('year', 'N/A')})\n"
            else:
                output += f"• {detail.get('name', node_id)} ({detail.get('affiliation', 'N/A')})\n"
            output += f"  {metric} centrality: {score:.4f}\n\n"

        return {"content": [{"type": "text", "text": output}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error calculating centrality: {str(e)}"}]}

    finally:
        await driver.close()


@tool(
    name="detect_communities",
    description="Detect research communities in the citation or collaboration network",
    params={
        "algorithm": {
            "type": "string",
            "enum": ["louvain", "label_propagation"],
            "description": "Community detection algorithm",
            "default": "louvain"
        },
        "network_type": {
            "type": "string",
            "enum": ["citation", "collaboration"],
            "description": "Type of network to analyze",
            "default": "citation"
        },
        "min_size": {
            "type": "number",
            "description": "Minimum community size to report",
            "default": 5
        }
    }
)
async def detect_communities(args):
    algorithm = args["algorithm"]
    network_type = args.get("network_type", "citation")
    min_size = args.get("min_size", 5)

    # Implementation similar to calculate_centrality
    # Fetch network, build graph, run community detection

    # Placeholder output
    output = f"Detected communities using {algorithm} on {network_type} network:\n\n"
    output += "Community 1 (234 papers): Social Network Analysis\n"
    output += "Community 2 (189 papers): Biological Networks\n"
    output += "Community 3 (156 papers): Infrastructure & Transportation\n"

    return {"content": [{"type": "text", "text": output}]}
```

#### Step 4: Create Main Agent

`agent.py`:

```python
#!/usr/bin/env python3

import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    ToolUseBlock
)
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Import your tools
from tools.graph_tools import query_knowledge_graph, find_papers_by_topic
from tools.network_tools import calculate_centrality, detect_communities

console = Console()

SYSTEM_PROMPT = """
You are a world-class network science expert with deep knowledge of:
- Graph theory and network analysis
- Centrality measures and their interpretations
- Community detection algorithms
- Network models and their properties
- Research methodology in network science

Your approach:
1. Understand the user's question - ask for clarification if needed
2. Plan your analysis using appropriate tools and metrics
3. Execute queries and calculations
4. Interpret results in network science context
5. Provide clear, educational explanations

When asked about concepts, explain them rigorously with examples.
When asked to analyze data, use the tools to query the knowledge graph and calculate metrics.
Always ground your answers in network science theory.
"""

async def main():
    # Create tools server
    tools = create_sdk_mcp_server(
        name="network-science",
        version="1.0.0",
        tools=[
            query_knowledge_graph,
            find_papers_by_topic,
            calculate_centrality,
            detect_communities
        ]
    )

    # Configure agent
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"nettools": tools},
        allowed_tools=[
            "mcp__nettools__query_knowledge_graph",
            "mcp__nettools__find_papers_by_topic",
            "mcp__nettools__calculate_centrality",
            "mcp__nettools__detect_communities"
        ]
    )

    # Welcome message
    console.print(Panel.fit(
        "[bold cyan]Network Science Expert Agent[/bold cyan]\n\n"
        "Ask me about network science, or let me analyze your research graph!",
        title="🔬 Welcome"
    ))

    # Agent loop
    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if user_input.lower() in ["exit", "quit"]:
                break

            await client.query(user_input)

            console.print("\n[bold blue]Agent[/bold blue]:")

            response_text = ""
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            console.print(f"[dim]⚙️  {block.name}[/dim]")

            console.print(Markdown(response_text))

if __name__ == "__main__":
    asyncio.run(main())
```

#### Step 5: Run and Test

```bash
# Start Neo4j (if not already running)
docker run -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password neo4j

# Run agent
python agent.py
```

**Example interactions:**

```
You: What is betweenness centrality and when should I use it?

Agent: Betweenness centrality is a measure of a node's importance based on its
position in connecting other nodes. Specifically, it quantifies how often a node
lies on the shortest paths between other pairs of nodes.

Mathematically, for node v:
C_B(v) = Σ(σ_st(v) / σ_st)

where σ_st is the total number of shortest paths from s to t, and σ_st(v) is
the number of those paths that pass through v.

When to use it:
1. Identifying "bridges" or brokers in networks
2. Finding bottlenecks in information flow
3. Detecting influential spreaders in diffusion processes
4. Analyzing control points in infrastructure networks

Would you like me to calculate betweenness centrality for your research graph?
```

```
You: Yes, find the papers with highest betweenness centrality

Agent: [⚙️  calculate_centrality]

Top 10 papers by betweenness centrality:

• "Network Science" by Barabási (2016)
  betweenness centrality: 0.2341

• "The Structure and Function of Complex Networks" by Newman (2003)
  betweenness centrality: 0.1876

...

These papers serve as crucial bridges between different research communities in
network science. The high betweenness of Barabási's "Network Science" reflects
its role in connecting multiple subfields.
```

### 9.3 Making It Goal-Oriented

Add explicit goal tracking:

```python
@tool(
    name="set_analysis_goal",
    description="Set a multi-step analysis goal that requires planning",
    params={
        "goal": {"type": "string", "description": "The analysis goal to achieve"}
    }
)
async def set_analysis_goal(args):
    goal = args["goal"]

    return {
        "content": [{
            "type": "text",
            "text": f"""Goal set: {goal}

I'll now create a plan to achieve this goal. Let me break it down into steps:

1. Identify what data I need from the knowledge graph
2. Determine appropriate metrics and algorithms
3. Execute analysis with proper tools
4. Verify results make sense
5. Interpret findings in network science context
6. Present conclusions and suggest follow-up analyses

Proceeding with Step 1..."""
        }]
    }


# Update system prompt to be more goal-oriented
GOAL_ORIENTED_PROMPT = SYSTEM_PROMPT + """

You are a GOAL-ORIENTED agent. When given a task:

1. **Explicitly state the goal** and your understanding of it
2. **Create a plan** with numbered steps
3. **Execute each step**, using tools as needed
4. **Verify each step's results** before proceeding
5. **Adapt your plan** if results suggest a different approach
6. **Confirm goal completion** when done

If the goal is ambiguous, ASK FOR CLARIFICATION before proceeding.
If you discover issues during execution, REPLAN rather than blindly continuing.
At the end, explicitly confirm: "Goal achieved: [summary]"
"""
```

---

## 10. Best Practices & Anti-Patterns

### 10.1 Best Practices

#### ✅ Design for Agency

**Good:**
```python
# Agent decides which tools to use based on goal
await client.query("Find the most influential papers in network science")
# Agent will plan: query graph → calculate centrality → rank → respond
```

**Bad:**
```python
# Hardcoded sequence (not agentic)
results1 = query_graph("MATCH (p:Paper) RETURN p")
results2 = calculate_centrality(results1)
results3 = rank_papers(results2)
```

#### ✅ Enable Self-Correction

**Good:**
```python
@tool("verify_query_results")
async def verify_query_results(args):
    """Agent can verify if query results make sense"""
    results = args["results"]
    expected = args["expected_properties"]

    # Check if results match expectations
    if validate(results, expected):
        return {"status": "valid"}
    else:
        return {"status": "invalid", "issues": list_issues(results)}
```

#### ✅ Design Tools for Workflows

**Good:**
```python
@tool("analyze_research_impact")
async def analyze_research_impact(args):
    """Complete workflow: fetch paper + citations + metrics"""
    paper_id = args["paper_id"]

    # Internally: fetch paper, get citations, calculate metrics, format output
    return comprehensive_impact_analysis(paper_id)
```

**Bad:**
```python
# Agent must orchestrate many low-level calls
@tool("get_paper")
@tool("get_citations")
@tool("count_citations")
@tool("format_output")
```

#### ✅ Provide Rich Context

**Good:**
```python
# CLAUDE.md includes domain knowledge
"""
## Network Science Concepts

**Centrality Measures:**
- Degree: Count of connections
- Betweenness: Bridge importance
...

## Common Patterns in Our Data

Citation networks typically show:
- Power-law degree distributions
- Small-world properties (high clustering, short paths)
...
"""
```

#### ✅ Use Hooks for Safety

**Good:**
```python
async def prevent_destructive_ops(context, hook_input):
    query = hook_input.input.get("query", "")
    if any(op in query.lower() for op in ["delete", "drop", "remove"]):
        return {"permission": "deny", "reason": "Destructive operation blocked"}
    return {"permission": "allow"}
```

#### ✅ Enable Clarification

**Good:**
```python
# System prompt includes:
"""
If the user's question is ambiguous:
- DON'T guess what they mean
- DO ask specific clarifying questions
- Provide options: "Do you mean (1) X or (2) Y?"
"""
```

#### ✅ Implement Planning

**Good:**
```python
# System prompt includes:
"""
For complex tasks:
1. State your understanding of the goal
2. Create a step-by-step plan
3. Execute each step
4. Verify before proceeding
5. Adapt if needed
"""
```

#### ✅ Provide Feedback

**Good:**
```python
# Show what agent is doing
async for message in client.receive_response():
    if isinstance(message, ToolUseBlock):
        console.print(f"[dim]⚙️  {message.name}[/dim]")
```

### 10.2 Anti-Patterns

#### ❌ Hardcoded LLM Chains

```python
# DON'T: This is just a chain, not agentic
def bad_agent(query):
    step1 = llm("Extract keywords from: " + query)
    step2 = database.search(step1)
    step3 = llm("Summarize: " + step2)
    return step3
```

#### ❌ Tools That Return Too Much Data

```python
# DON'T: Wastes context
@tool("dump_all_papers")
async def dump_all_papers(args):
    # Returns 50,000 papers - fills context window!
    return {"papers": database.get_all()}
```

#### ❌ No Verification Steps

```python
# DON'T: Agent can't verify its work
async def bad_workflow():
    await client.query("Find influential papers")
    # Agent runs tools and returns results
    # No way to verify if results make sense
```

#### ❌ Ambiguous Tool Names

```python
# DON'T: Unclear what tool does
@tool("process", "Process data")

# DO: Clear naming
@tool("calculate_betweenness_centrality", "Calculate betweenness centrality for network nodes")
```

#### ❌ Ignoring Errors

```python
# DON'T: Fails silently
try:
    result = await query_graph(bad_query)
except:
    pass  # Agent doesn't know query failed
```

#### ❌ Too Many Tools

```python
# DON'T: 50+ tools overwhelming the agent
# DO: 5-15 well-designed workflow tools
```

#### ❌ No Memory Management

```python
# DON'T: Agent forgets everything between sessions
# DO: Use CLAUDE.md, memory tools, or persistent storage
```

### 10.3 Performance Considerations

#### Optimize Tool Latency

```python
# Use connection pooling for databases
from neo4j import AsyncGraphDatabase

class GraphDBPool:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(URI, auth=AUTH)

    async def query(self, cypher):
        async with self.driver.session() as session:
            result = await session.run(cypher)
            return await result.data()

    async def close(self):
        await self.driver.close()

# Reuse across tool calls
db_pool = GraphDBPool()
```

#### Cache Expensive Computations

```python
from functools import lru_cache
import hashlib

# Cache network metrics
metric_cache = {}

async def calculate_centrality_cached(graph_hash, metric):
    cache_key = f"{graph_hash}_{metric}"

    if cache_key in metric_cache:
        return metric_cache[cache_key]

    # Compute
    result = await calculate_centrality(metric)
    metric_cache[cache_key] = result

    return result
```

#### Batch Operations

```python
# DON'T: N queries for N papers
for paper_id in paper_ids:
    paper = await get_paper(paper_id)

# DO: Single batch query
papers = await get_papers_batch(paper_ids)
```

---

## 11. Production Deployment

### 11.1 Error Handling

```python
from claude_agent_sdk import ClaudeSDKError, CLIConnectionError

async def production_agent():
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_query)

            async for message in client.receive_response():
                try:
                    handle_message(message)
                except ToolError as e:
                    logger.error(f"Tool error: {e}")
                    await client.query(f"The tool failed with error: {e}. Please try an alternative approach.")

    except CLIConnectionError:
        logger.error("Claude Code not available")
        return "Service temporarily unavailable"

    except ClaudeSDKError as e:
        logger.error(f"SDK error: {e}")
        return "An error occurred processing your request"

    except Exception as e:
        logger.exception("Unexpected error")
        return "An unexpected error occurred"
```

### 11.2 Monitoring

```python
import logging
from datetime import datetime

class AgentMonitor:
    def __init__(self):
        self.metrics = {
            "queries": 0,
            "tool_calls": {},
            "errors": 0,
            "avg_response_time": 0
        }

    def log_query(self, query: str):
        self.metrics["queries"] += 1
        logger.info(f"Query: {query}")

    def log_tool_use(self, tool_name: str):
        self.metrics["tool_calls"][tool_name] = \
            self.metrics["tool_calls"].get(tool_name, 0) + 1
        logger.info(f"Tool used: {tool_name}")

    def log_error(self, error: Exception):
        self.metrics["errors"] += 1
        logger.error(f"Error: {error}", exc_info=True)

    def get_metrics(self):
        return self.metrics

monitor = AgentMonitor()

async def monitored_agent(query):
    monitor.log_query(query)
    start_time = datetime.now()

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(query)

            async for message in client.receive_response():
                if isinstance(message, ToolUseBlock):
                    monitor.log_tool_use(message.name)

    except Exception as e:
        monitor.log_error(e)
        raise

    finally:
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Query completed in {duration}s")
```

### 11.3 Rate Limiting

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, time_window: timedelta):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def acquire(self):
        now = datetime.now()

        # Remove old requests
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] + self.time_window - now).total_seconds()
            await asyncio.sleep(wait_time)

        self.requests.append(now)

# 10 requests per minute
rate_limiter = RateLimiter(max_requests=10, time_window=timedelta(minutes=1))

async def rate_limited_agent(query):
    await rate_limiter.acquire()

    async with ClaudeSDKClient(options=options) as client:
        await client.query(query)
        # ...
```

### 11.4 Docker Deployment

`Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install Node.js for Claude Code
RUN apt-get update && apt-get install -y nodejs npm

# Install Claude Code
RUN npm install -g @anthropic/claude-code

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NEO4J_URI=bolt://neo4j:7687

# Run agent
CMD ["python", "agent.py"]
```

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15
    environment:
      - NEO4J_AUTH=neo4j/password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  agent:
    build: .
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - neo4j
    stdin_open: true
    tty: true

volumes:
  neo4j_data:
```

---

## 12. Resources & Links

### 12.1 Official Documentation

- **Claude Agent SDK Docs**: https://docs.claude.com/en/api/agent-sdk/overview
- **Python SDK Reference**: https://docs.claude.com/en/api/agent-sdk/python
- **MCP Documentation**: https://docs.claude.com/en/api/agent-sdk/mcp
- **Anthropic Engineering Blog**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

### 12.2 GitHub Repositories

- **Python SDK**: https://github.com/anthropics/claude-agent-sdk-python
- **TypeScript SDK**: https://github.com/anthropics/claude-agent-sdk-typescript
- **Demo Applications**: https://github.com/anthropics/claude-agent-sdk-demos
- **Tutorial Repository**: https://github.com/kenneth-liao/claude-agent-sdk-intro

### 12.3 Tutorials & Guides

- **DataCamp Tutorial**: https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk
- **Agent Design Lessons**: https://jannesklaas.github.io/ai/2025/07/20/claude-code-agent-design.html
- **Best Practices 2025**: https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/
- **Claude Code Best Practices**: https://www.anthropic.com/engineering/claude-code-best-practices

### 12.4 Community Resources

- **Awesome Claude Agents**: https://github.com/rahulvrane/awesome-claude-agents
- **Sub-Agents Collection**: https://github.com/lst97/claude-code-sub-agents
- **MCP Servers**: https://github.com/modelcontextprotocol/servers

### 12.5 Network Science Resources

- **Neo4j Knowledge Graphs**: https://neo4j.com/blog/developer/knowledge-graphs-claude-neo4j-mcp/
- **GraphAgent Research**: https://arxiv.org/html/2412.17029v1
- **Graph + AI Agents**: https://arxiv.org/html/2506.18019v1

### 12.6 Key Concepts Papers

- **Agentic AI vs LLM Chains**: https://medium.com/@jeevitha.m/agents-vs-llm-pipelines-beyond-simple-chains-understanding-the-paradigm-shift-1bed32ec2ebd
- **Reflection Pattern**: https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-2-reflection/
- **MCP Design Patterns**: https://dev.to/klavisai/less-is-more-4-design-patterns-for-building-better-mcp-servers-3gpf

---

## Conclusion

Building a truly agentic network science expert requires:

1. **Goal-Oriented Design**: The agent should work toward objectives, not just execute steps
2. **Feedback Loops**: Continuous cycle of gather context → act → verify → repeat
3. **Tool Orchestration**: Well-designed tools that enable autonomous decision-making
4. **Self-Correction**: Ability to verify work and adapt approach
5. **Natural Interaction**: Can ask for clarification and maintain conversation context
6. **Domain Expertise**: System prompt with deep network science knowledge
7. **Memory Management**: Short-term (session) and long-term (CLAUDE.md, tools) memory
8. **Production-Ready**: Error handling, monitoring, rate limiting, deployment

The Claude Agent SDK provides all the building blocks you need. The key differentiator is how you design your agent's:
- System prompt (expertise + approach)
- Tools (workflow-based, not raw APIs)
- Goal tracking and verification
- Memory and state management

Your network science agent should be able to:
- Accept natural language questions about network science
- Plan multi-step analyses autonomously
- Query your knowledge graph intelligently
- Calculate appropriate metrics
- Ask for clarification when needed
- Explain findings in network science context
- Maintain conversation memory
- Self-correct when results don't make sense

This is the difference between an "agentic system" and "LLM chains" - true agency comes from autonomous goal pursuit, not scripted sequences.

---

**Report compiled**: 2025-11-06
**Research scope**: Claude Agent SDK (Python), agentic AI patterns, network science applications
**Sources**: 20+ documentation sites, research papers, tutorials, and code repositories
