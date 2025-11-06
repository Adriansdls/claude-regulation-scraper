# 🔬 Research Graph Explorer

**AI-powered research paper discovery and network analysis system for achieving 100% recall and finding literature gaps.**

> **Status**: 🚧 Active Development - Phase 3.1 (Advanced Graph Algorithms) ✅
> - ✅ Phase 1: Discovery Engine
> - ✅ Phase 2: Knowledge Extraction
> - ✅ Phase 3.1: Graph Algorithms & Dynamic Execution
> - 🚧 Phase 3.2: Agentic System (Next!)

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

```bash
# Clone repository
git clone <repository-url>
cd research-graph-explorer

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
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

# Phase 3: Analyze the network
python
from src.analysis import GraphAnalyzer, DynamicGraphQueryExecutor
from src.extraction import KnowledgeGraph

kg = KnowledgeGraph.load("knowledge_graph.json")
analyzer = GraphAnalyzer(kg)

# Find literature gaps
gaps = analyzer.detect_gaps()
print(f"Found {len(gaps)} gaps")

# Detect echo chambers
chambers = analyzer.find_echo_chambers()

# Or use dynamic queries for custom analyses
dynamic = DynamicGraphQueryExecutor(kg)
result = dynamic.query("your custom NetworkX code here")
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

## 🛠️ Technology Stack

- **LLMs**: Anthropic Claude, OpenAI GPT-4
- **Extraction**: Google LangExtract
- **Paper APIs**: Semantic Scholar, arXiv, CrossRef, PubMed
- **Graph**: NetworkX, python-igraph, Neo4j (optional)
- **PDF**: PyMuPDF, PDFPlumber
- **Storage**: SQLite/PostgreSQL, Redis
- **CLI**: Click, Rich

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

### 🚧 Phase 3: Analysis (Next)
- [ ] Gap detection algorithms
- [ ] Echo chamber detection
- [ ] Citation ring finding
- [ ] Argument weakness analysis
- [ ] Interdisciplinary bridge detection
- [ ] Emerging trend identification
- [ ] Research opportunity finder

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
