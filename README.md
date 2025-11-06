# 🔬 Research Graph Explorer

**AI-powered research paper discovery and network analysis system for achieving 100% recall and finding literature gaps.**

> **Status**: 🎉 **COMPLETE** - Ready for Research!
> - ✅ Phase 1: Discovery Engine
> - ✅ Phase 2: Knowledge Extraction
> - ✅ Phase 3.1: Graph Algorithms & Dynamic Execution
> - ✅ Phase 3.2: Agentic System - **Chat with your research graph in natural language!**

---

## 🎯 What is This?

Research Graph Explorer is an ambitious system that:

1. **Discovers ALL relevant papers** for a research question (100% recall goal)
   - Uses citation network traversal (frontier-based exploration)
   - Multi-modal satellite discovery (APIs, author-based, venue-based)
   - Smart relevance scoring with LLMs

2. **Extracts structured knowledge** using custom ontologies
   - LLM-powered extraction with Google's LangExtract
   - User-defined entities and relationships
   - Multi-layer knowledge graph construction

3. **Finds research opportunities** through network science
   - Literature gap detection
   - Echo chamber identification
   - Argument weakness analysis
   - Emerging trend spotting

---

## 🚀 Quick Start

### Installation

**Option 1: Install from Git (Recommended)**
```bash
pip install git+https://github.com/Adriansdls/claude-regulation-scraper.git
```

**Option 2: Local Development**
```bash
git clone <repository-url>
cd research-graph-explorer
pip install -e .
```

**Option 3: From Wheel**
```bash
# Build distribution
python -m build
pip install dist/research_graph_explorer-2.0.0-py3-none-any.whl
```

**Quick Test:**
```bash
rge --help
python scripts/verify_install.py
```

**See [QUICKSTART.md](QUICKSTART.md) for 3-minute test guide!**
**See [INSTALL.md](INSTALL.md) for detailed installation options.**

### Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY (required for agent)
# - OPENAI_API_KEY (optional)
# - SEMANTIC_SCHOLAR_API_KEY (optional)
```

### Basic Usage

```bash
# Phase 1: Discover papers
python -m src.cli.main discover \
  "What are the latest advances in transformer architectures for NLP?" \
  --max-papers 100 \
  --output papers.json

# Phase 2: Extract knowledge using an ontology
python -m src.cli.main extract papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output knowledge_graph.json

# Phase 3: Interactive Chat with your research graph! ✨
rge chat knowledge_graph.json

╭─────────────────────────────────────────────────────────────────╮
│          🧠 Network Science Research Assistant [Enhanced]       │
│                                                                 │
│  ✨ New Features: Multi-line • Autocomplete • Plots • Costs   │
╰─────────────────────────────────────────────────────────────────╯

You: find gap[Tab]
     → "find gaps in the literature"  [autocomplete!]

You: find gaps in graph neural networks

Agent: I'll analyze the GNN literature for gaps...
→ Using detect_gaps... ✓

Found 12 potential gaps:

Gap Importance Distribution
0.9┤             ●
0.8┤          ●     ●
0.7┤       ●           ●
0.6┤    ●                 ●
   └──────────────────────────
      [Terminal plot!]

Top 3 gaps:
1. ISOLATED IMPORTANT CONCEPT: "Graph pooling methods"
   - PageRank: 0.892 (highly important)
   - Only 2 connections (underexplored)

2. MISSING LINK: "Graph attention" ↔ "Spectral methods"
   - 87% similarity but no connection

[Status: Q#2 | $0.12 | 1.2s]  [Real-time cost tracking!]

You: find papers that: \          [Multi-line mode!]
... - cite both of these concepts
... - were published after 2020
... [Ctrl+D]

Agent: Searching for papers matching your criteria...
→ Using dynamic_graph_query... ✓

# NetworkX code with syntax highlighting:
papers = [p for p in kg.papers
          if p['year'] > 2020
          and has_both_concepts(p)]

Found 8 papers! [Shows results...]

# Or use programmatically:
python
from src.analysis import GraphAnalyzer, DynamicGraphQueryExecutor
from src.extraction import KnowledgeGraph

kg = KnowledgeGraph.load("knowledge_graph.json")
analyzer = GraphAnalyzer(kg)

# Find literature gaps
gaps = analyzer.detect_gaps()

# Or write custom NetworkX code dynamically!
dynamic = DynamicGraphQueryExecutor(kg)
result = dynamic.query("your custom code here")
```

---

## 📐 Architecture

### Three-Phase System

```
Phase 1: Discovery       Phase 2: Extraction      Phase 3: Analysis
┌──────────────┐         ┌─────────────────┐      ┌──────────────────┐
│ Research     │         │ LangExtract     │      │ Gap Detection    │
│ Question     │ ──────> │ Knowledge Graph │ ───> │ Network Science  │
│              │         │                 │      │ Opportunities    │
└──────────────┘         └─────────────────┘      └──────────────────┘
     │                           │                         │
     │                           │                         │
   Papers                    Entities                  Insights
```

### Phase 1: Discovery Engine ✅

- **Seed Generator**: Converts research question to seed papers
- **Frontier Explorer**: BFS/DFS with relevance scoring
- **Satellite Finder**: Discovers disconnected papers
- **Multi-Source Fetcher**: Semantic Scholar, arXiv, CrossRef, PubMed
- **PDF Processor**: Acquisition and text extraction

### Phase 2: Knowledge Extraction ✅

- **Ontology Manager**: User-defined schemas (YAML)
- **LangExtract Integration**: Entity and relationship extraction
- **Knowledge Graph**: Multi-layer graph (papers + concepts)
- **PDF Processing**: Multi-source download with fallbacks
- **Text Extraction**: PyMuPDF + pdfplumber with quality scoring

### Phase 3.1: Advanced Graph Algorithms ✅

- **GraphAnalyzer**: Pre-defined algorithms for common operations
  - Community detection (Louvain, Leiden, Label Propagation)
  - Centrality metrics (PageRank, Betweenness, Closeness, Eigenvector)
  - Gap detection (isolated concepts, missing links)
  - Echo chamber detection (citation rings)
  - Path analysis, Author network analysis
- **DynamicGraphQueryExecutor**: LLM-generated NetworkX code execution
  - Safe sandbox (timeout, validation, restricted imports)
  - Handles novel queries we didn't anticipate!

### Phase 3.2: Agentic System (Next)

- **NetworkScienceAgent**: Goal-oriented research assistant
- **Claude Agents SDK Integration**: True agency, not LLM chains
- **Interactive Chat Mode**: Beautiful terminal UX
- **Natural Language Queries**: Ask questions, get analyses
- **TodoWrite Transparency**: See agent's thinking and planning

### Phase 3: Network Analysis (Coming Soon)

- **Gap Detection**: Find under-explored areas
- **Echo Chamber Detection**: Identify citation rings
- **Opportunity Finder**: Interdisciplinary bridges, trends

---

## 📁 Project Structure

```
research-graph-explorer/
├── src/
│   ├── discovery/          # Phase 1: Paper discovery
│   ├── extraction/         # Phase 2: Knowledge extraction
│   ├── analysis/           # Phase 3: Network analysis
│   ├── models/             # Data models
│   ├── infrastructure/     # Core infrastructure
│   ├── utils/              # Utilities
│   └── cli/                # Command-line interface
├── config/
│   └── ontologies/         # Ontology definitions
├── data/                   # Local data storage
├── notebooks/              # Jupyter notebooks
├── tests/                  # Tests
└── scripts/                # Utility scripts
```

---

## ✨ Enhanced Terminal Experience

The chat interface features a **world-class UX** inspired by Claude Code, GitHub CLI, and modern terminal tools:

### 🎯 Key Features

**1. Multi-line Input**
- End queries with `\` for multi-line mode
- Perfect for complex, multi-criteria questions
- Visual feedback and easy submission (Ctrl+D)

**2. Smart Autocomplete**
- Press Tab for intelligent suggestions
- Query templates, commands, graph entities
- Fuzzy matching and context-aware
- Discovers ~100+ paper titles, authors, concepts from your graph

**3. Terminal Plots**
- Beautiful ASCII visualizations right in your terminal
- Histograms, bar charts, line plots, scatter plots
- Community sizes, centrality distributions, timelines
- Powered by `plotext`

**4. Token & Cost Tracking**
- Real-time usage monitoring
- Detailed cost breakdown (input/output/cache)
- Session statistics with plots
- Budget awareness: always know what you're spending

**5. Syntax Highlighting**
- Python/NetworkX code beautifully highlighted
- JSON data formatted
- Inline code marked
- Powered by Pygments

**6. Status Bar**
- Persistent context awareness
- Shows: graph name, query count, session cost, model
- Query timing and performance metrics

**7. Commands**
```bash
help      # Example queries & templates
stats     # Graph statistics with plots
memory    # Saved insights
usage     # Detailed cost breakdown
clear     # Reset conversation
exit      # Exit with session summary
```

**See `UX_FEATURES_GUIDE.md` for complete documentation!**

---

## 🛠️ Technology Stack

**Core:**
- **LLMs**: Anthropic Claude, OpenAI GPT-4
- **Extraction**: Google LangExtract
- **Paper APIs**: Semantic Scholar, arXiv, CrossRef, PubMed
- **Graph**: NetworkX, python-igraph, Leiden/Louvain
- **PDF**: PyMuPDF, PDFPlumber
- **Storage**: SQLite/PostgreSQL, Redis

**Terminal UX:**
- **CLI**: Click, Rich, prompt-toolkit
- **Plots**: plotext
- **Highlighting**: Pygments
- **Tokens**: tiktoken

---

## 📊 Current Status

### ✅ Phase 1: Discovery (Complete)
- [x] Architecture design
- [x] Project structure
- [x] Core data models (Paper, Author, Citation)
- [x] API clients (Semantic Scholar, arXiv)
- [x] Seed generator with LLM-powered queries
- [x] Frontier-based explorer with relevance scoring
- [x] Multi-source paper fetcher with fallback
- [x] CLI interface for discovery
- [x] Caching and infrastructure

### ✅ Phase 2: Extraction (Complete!)
- [x] PDF acquisition pipeline (arXiv, Unpaywall, DOI)
- [x] Text extraction (PyMuPDF, pdfplumber)
- [x] Structured text parsing (sections detection)
- [x] LangExtract integration for entities
- [x] Relationship extraction
- [x] Knowledge graph construction (NetworkX)
- [x] Extraction orchestrator
- [x] CLI commands for extraction
- [x] Gephi export for visualization

### ✅ Phase 3.1: Graph Algorithms (Complete!)
- [x] Community detection (Louvain, Leiden, Label Propagation)
- [x] Centrality metrics (PageRank, Betweenness, Closeness, Degree, Eigenvector)
- [x] Gap detection algorithms (isolated concepts, missing links, disconnected communities)
- [x] Echo chamber detection (citation rings, self-referential clusters)
- [x] Path analysis (shortest paths, knowledge flow)
- [x] Author network analysis (co-authorship, collaboration patterns)
- [x] Dynamic code execution (safe NetworkX code sandbox)

### ✅ Phase 3.2: Agentic System (Complete! 🎉)
- [x] True agentic architecture (autonomous, goal-oriented)
- [x] 12 specialized tools (graphs + dynamic + memory + visualization)
- [x] Natural language interface
- [x] Memory system (persistent insights across sessions)
- [x] Interactive chat CLI
- [x] **Enhanced UX** (multi-line, autocomplete, plots, cost tracking)
- [x] Comprehensive documentation

---

## 🤝 Contributing

This project is in active development. Contributions welcome!

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

- **Google LangExtract**: Knowledge extraction framework
- **Semantic Scholar**: Paper discovery API
- **arXiv**: Open access preprints
- **NetworkX**: Graph processing

---

**Built with 🧠 for researchers who want to find EVERYTHING relevant to their work.**
