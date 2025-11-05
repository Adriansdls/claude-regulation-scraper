# 🔬 Research Graph Explorer

**AI-powered research paper discovery and network analysis system for achieving 100% recall and finding literature gaps.**

> **Status**: 🚧 Active Development - Phase 1 (Discovery Engine)

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
# Discover papers for a research question
rgx discover "What are the latest advances in transformer architectures for NLP?"

# Extract knowledge using an ontology
rgx extract --ontology config/ontologies/ml_research.yaml

# Analyze the network
rgx analyze --find-gaps --find-opportunities

# Visualize the graph
rgx visualize --output graph.html
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

### Phase 1: Discovery Engine (Current Focus)

- **Seed Generator**: Converts research question to seed papers
- **Frontier Explorer**: BFS/DFS with relevance scoring
- **Satellite Finder**: Discovers disconnected papers
- **Multi-Source Fetcher**: Semantic Scholar, arXiv, CrossRef, PubMed
- **PDF Processor**: Acquisition and text extraction

### Phase 2: Knowledge Extraction (Coming Soon)

- **Ontology Manager**: User-defined schemas
- **LangExtract Integration**: Entity and relationship extraction
- **Knowledge Graph**: Multi-layer graph construction

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

### ✅ Completed
- [x] Architecture design
- [x] Project structure
- [x] Dependencies setup

### 🚧 In Progress
- [ ] Core data models
- [ ] API clients (Semantic Scholar, arXiv)
- [ ] Seed generator
- [ ] Frontier explorer

### 📋 Planned
- [ ] PDF acquisition pipeline
- [ ] LangExtract integration
- [ ] Knowledge graph construction
- [ ] Network analysis algorithms
- [ ] CLI interface
- [ ] Documentation

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
