# 🧪 User Testing Guide - Run This On Your Machine!

**Important**: This environment lacks internet. Please run these tests on YOUR local machine where you have network access.

---

## 🎯 Quick Start

### 1. Install Latest Version
```bash
pip uninstall research-graph-explorer -y
pip cache purge
pip install --no-cache-dir --force-reinstall "git+https://github.com/Adriansdls/claude-regulation-scraper.git@claude/research-question-app-011CUqbir4zupwJ84dNSwGRo"
```

### 2. Configure API Keys
Create/edit `.env` in your working directory:
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
DEFAULT_LLM=anthropic

# Optional: For higher rate limits
# SEMANTIC_SCHOLAR_API_KEY=your-s2-api-key-here
```

**Note**: Replace the placeholder keys above with your actual API keys.

### 3. Verify Setup
```bash
rge config-check
```

You should see:
- ✓ Anthropic API Key: Set
- ✓ OpenAI API Key: Set
- ✓ Configuration is valid

---

##Human: no worries for now, as we know it should work now. The question that I have is on your last commit. You update the model for network agent. You need to update in any other spot? THat is the only spot you updated the model besides config?