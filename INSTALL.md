# Installation Guide - Research Graph Explorer

**Quick test installation for yourself or team members.**

---

## 📦 Installation Methods

### Method 1: Install from Git (Easiest for Testing)

**Install directly from GitHub:**
```bash
# Install latest from your branch
pip install git+https://github.com/Adriansdls/claude-regulation-scraper.git@claude/research-question-app-011CUqbir4zupwJ84dNSwGRo

# Or from main branch (once merged)
pip install git+https://github.com/Adriansdls/claude-regulation-scraper.git
```

After installation, the `rge` command will be available globally!

```bash
# Test it works
rge --help

# Run chat
rge chat knowledge_graph.json
```

---

### Method 2: Local Development Install (Best for Development)

**For active development with hot-reload:**

```bash
# Clone the repository
git clone https://github.com/Adriansdls/claude-regulation-scraper.git
cd claude-regulation-scraper

# Checkout the enhanced branch
git checkout claude/research-question-app-011CUqbir4zupwJ84dNSwGRo

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

**Editable mode (`-e`) means:**
- Changes to code are immediately reflected
- No need to reinstall after edits
- Perfect for development

**Test it:**
```bash
rge --help
rge chat knowledge_graph.json
```

---

### Method 3: Install from Local Directory

**Share via folder/zip with a colleague:**

```bash
# Get the code (clone or download zip)
git clone https://github.com/Adriansdls/claude-regulation-scraper.git
cd claude-regulation-scraper

# Install normally
pip install .

# Or with optional dependencies
pip install ".[dev,neo4j]"
```

**Share the folder:**
```bash
# Zip it
zip -r research-graph-explorer.zip claude-regulation-scraper/

# Send to colleague, they can:
unzip research-graph-explorer.zip
cd claude-regulation-scraper
pip install .
```

---

### Method 4: Build Wheel (For Distribution)

**Create installable wheel file:**

```bash
# Install build tools
pip install build

# Build distribution
python -m build

# This creates:
# - dist/research_graph_explorer-2.0.0-py3-none-any.whl
# - dist/research-graph-explorer-2.0.0.tar.gz
```

**Install the wheel:**
```bash
pip install dist/research_graph_explorer-2.0.0-py3-none-any.whl
```

**Share the wheel:**
- Email the `.whl` file
- Upload to internal server
- Recipients install: `pip install research_graph_explorer-2.0.0-py3-none-any.whl`

---

### Method 5: Private PyPI Server (Advanced)

**For teams - internal package index:**

```bash
# Option A: Use devpi (private PyPI)
pip install devpi-server devpi-web
devpi-server --init
devpi-server --start

# Upload your package
devpi use http://localhost:3141
devpi user -c myuser password=secret
devpi login myuser --password=secret
devpi index -c dev
devpi use myuser/dev
devpi upload

# Team members install:
pip install --index-url http://localhost:3141/myuser/dev/+simple/ research-graph-explorer
```

**Option B: Simple HTTP server:**
```bash
# Build wheels
python -m build

# Serve directory
cd dist/
python -m http.server 8000

# Team installs:
pip install http://yourserver:8000/research_graph_explorer-2.0.0-py3-none-any.whl
```

---

## 🧪 Quick Test

After any installation method:

```bash
# Check version
rge --version

# Show help
rge --help

# Test the enhanced chat (requires knowledge graph)
# If you don't have one, create a test one:
echo '{"papers": [], "entities": [], "relationships": []}' > test_graph.json
rge chat test_graph.json

# Should see the beautiful welcome screen!
```

---

## 🔧 Requirements

### System Requirements
- **Python**: 3.10 or higher
- **OS**: Linux, macOS, Windows
- **RAM**: 4GB minimum, 8GB+ recommended (for large graphs)

### API Keys (Optional)

For full functionality, set up API keys:

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your keys:
# - ANTHROPIC_API_KEY (for Claude)
# - OPENAI_API_KEY (optional, for GPT)
# - SEMANTIC_SCHOLAR_API_KEY (optional, higher rate limits)
```

**Without API keys:**
- Discovery and extraction won't work
- Chat analysis features work if you have a pre-built graph
- Graph algorithms work offline

---

## 📦 Dependency Groups

**Core (always installed):**
- LLMs: anthropic, openai, tiktoken
- Graph: networkx, python-igraph, leidenalg
- CLI/UX: rich, prompt-toolkit, plotext, pygments
- Paper APIs: semanticscholar, arxiv
- PDF: pymupdf, pdfplumber

**Optional groups:**

```bash
# Development tools
pip install ".[dev]"
# Adds: pytest, black, ruff, mypy, jupyter

# Neo4j support
pip install ".[neo4j]"
# Adds: neo4j driver

# Everything
pip install ".[all]"
```

---

## 🚀 Usage After Install

Once installed, you have the `rge` command:

```bash
# Phase 1: Discover papers
rge discover "What are the latest advances in transformers?" \
    --max-papers 100 \
    --output papers.json

# Phase 2: Extract knowledge
rge extract papers.json \
    --ontology config/ontologies/ml_research.yaml \
    --output knowledge_graph.json

# Phase 3: Interactive chat with enhanced UX! ✨
rge chat knowledge_graph.json
```

---

## 🔄 Updating

### From Git
```bash
pip install --upgrade git+https://github.com/Adriansdls/claude-regulation-scraper.git
```

### Editable Install
```bash
cd claude-regulation-scraper
git pull
# Changes are automatically reflected
```

### From Wheel
```bash
# Get new wheel, then:
pip install --upgrade --force-reinstall research_graph_explorer-2.0.0-py3-none-any.whl
```

---

## ❌ Uninstall

```bash
pip uninstall research-graph-explorer
```

---

## 🐛 Troubleshooting

### "rge command not found"

**Solution 1: Check pip installed to correct Python**
```bash
which python
which pip
python -m pip install -e .
```

**Solution 2: Add pip's script directory to PATH**
```bash
# Linux/Mac
export PATH="$HOME/.local/bin:$PATH"

# Windows
# Add %USERPROFILE%\AppData\Local\Programs\Python\Python3XX\Scripts to PATH
```

**Solution 3: Run directly**
```bash
python -m src.cli.main --help
```

### Installation fails with dependency errors

**Try installing dependencies manually first:**
```bash
# Install problematic packages first
pip install leidenalg  # May need C compiler
pip install python-igraph  # May need igraph C library

# On Ubuntu/Debian:
sudo apt-get install python3-dev libigraph-dev

# On macOS:
brew install igraph

# Then install package
pip install .
```

### ImportError after installation

**Ensure you're not in the source directory:**
```bash
cd ~
rge --help  # Should work now
```

### Plots not showing

```bash
pip install plotext>=5.2.8
```

### Autocomplete not working

```bash
pip install prompt-toolkit>=3.0.0
```

---

## 📊 Verify Installation

**Complete verification:**

```bash
# Check all commands available
rge --help

# Check version
python -c "import importlib.metadata; print(importlib.metadata.version('research-graph-explorer'))"

# Check key imports
python -c "
from src.cli.main import cli
from src.agent import NetworkScienceAgent
from src.analysis import GraphAnalyzer
from src.cli.ui import TerminalPlotter, QueryCompleter
print('✅ All imports successful!')
"

# Test CLI
rge discover --help
rge extract --help
rge chat --help
```

---

## 📤 Sharing with Team

### Quick Share (Git)

**Send this to colleagues:**
```bash
pip install git+https://github.com/Adriansdls/claude-regulation-scraper.git
```

### Package Share (Wheel)

**1. Build wheel:**
```bash
python -m build
```

**2. Share `dist/research_graph_explorer-2.0.0-py3-none-any.whl`**

**3. They install:**
```bash
pip install research_graph_explorer-2.0.0-py3-none-any.whl
```

### Source Share (Folder/Zip)

**1. Zip the repo:**
```bash
git archive --format=zip --output=research-graph-explorer-v2.0.0.zip HEAD
```

**2. They extract and install:**
```bash
unzip research-graph-explorer-v2.0.0.zip
cd research-graph-explorer-v2.0.0
pip install .
```

---

## 🌐 Publishing to PyPI (Future)

**When ready for public release:**

```bash
# 1. Create PyPI account at pypi.org

# 2. Install twine
pip install twine

# 3. Build distributions
python -m build

# 4. Upload to PyPI
twine upload dist/*

# 5. Anyone can install:
pip install research-graph-explorer
```

**For testing:**
```bash
# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ research-graph-explorer
```

---

## ✅ Success Checklist

After installation, verify:

- [ ] `rge --help` shows commands
- [ ] `rge chat --help` shows chat options
- [ ] Can import: `python -c "from src.agent import NetworkScienceAgent"`
- [ ] Terminal plots work: `python -c "from src.cli.ui import TerminalPlotter; print('✓')"`
- [ ] Autocomplete available: `python -c "import prompt_toolkit; print('✓')"`

**You're ready to explore research graphs!** 🚀

---

## 💡 Tips

1. **Development**: Always use `pip install -e .` for active coding
2. **Sharing**: Build wheel for easy distribution
3. **Teams**: Set up private PyPI or git-based install
4. **Production**: Wait for v2.1.0 for public PyPI release

---

## 📞 Support

**Issues during installation?**
- Check troubleshooting section above
- Verify Python 3.10+ installed
- Check all dependencies installed
- Try `pip install -e . --verbose` for detailed errors

**Everything working?**
```bash
rge chat your_graph.json
# Enjoy the world-class UX! ✨
```
