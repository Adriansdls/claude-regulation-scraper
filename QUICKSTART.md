# 🚀 Quick Start Guide

Get started with Research Graph Explorer in 5 minutes!

## 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys
```

## 2. Set API Keys

You need at least one LLM API key:

**.env file:**
```bash
# Required: Choose one
ANTHROPIC_API_KEY=your-key-here
# OR
OPENAI_API_KEY=your-key-here

# Optional (but recommended for higher rate limits)
SEMANTIC_SCHOLAR_API_KEY=your-key-here
```

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Semantic Scholar: https://www.semanticscholar.org/product/api

## 3. Verify Configuration

```bash
python -m src.cli.main config-check
```

## 4. Discover Papers

```bash
# Basic discovery (100 papers, threshold 0.6)
python -m src.cli.main discover "What are the latest advances in transformer architectures?"

# Custom parameters
python -m src.cli.main discover \
  "How can we detect echo chambers in citation networks?" \
  --max-papers 200 \
  --threshold 0.7 \
  --output results.json
```

## 5. Example Usage

### Example 1: NLP Research
```bash
python -m src.cli.main discover \
  "What are the most effective methods for few-shot learning in NLP?" \
  --max-papers 150 \
  --output nlp_few_shot.json
```

### Example 2: Computer Vision
```bash
python -m src.cli.main discover \
  "How have vision transformers improved over CNNs?" \
  --max-papers 100 \
  --threshold 0.65 \
  --output vision_transformers.json
```

### Example 3: Reinforcement Learning
```bash
python -m src.cli.main discover \
  "What are the latest advances in offline reinforcement learning?" \
  --max-papers 120 \
  --output offline_rl.json
```

## 6. Understanding Results

The system will:
1. **Generate seed papers** using LLM-powered query generation
2. **Explore the citation network** using frontier-based BFS
3. **Score papers** for relevance using LLM analysis
4. **Return relevant papers** sorted by relevance

Output includes:
- Paper metadata (title, authors, year, venue)
- Relevance score (0-1)
- Reasoning for relevance
- Citation count
- PDF links (if available)

## 7. Output Format

**Console output** shows:
- Seed papers table
- Real-time progress
- Discovery statistics
- Top 10 papers

**JSON output** (--output flag) contains:
```json
{
  "research_question": "...",
  "statistics": {
    "total_explored": 100,
    "total_relevant": 45,
    "relevance_rate": 0.45,
    "avg_relevance": 0.73
  },
  "papers": [
    {
      "paper_id": "...",
      "title": "...",
      "abstract": "...",
      "authors": ["...", "..."],
      "year": 2024,
      "relevance_score": 0.92,
      "relevance_reasoning": "...",
      "citation_count": 123,
      "pdf_url": "..."
    }
  ]
}
```

## 8. Tips for Better Results

### Craft Good Research Questions
✅ Good: "What are the latest advances in transformer architectures for NLP?"
✅ Good: "How can we improve sample efficiency in deep reinforcement learning?"
❌ Too broad: "Machine learning"
❌ Too specific: "GPT-3 paper by Brown et al."

### Adjust Parameters
- **--max-papers**: More papers = better recall, but slower
- **--threshold**: Higher threshold = higher precision, lower recall
  - 0.8+: Very strict (only directly relevant)
  - 0.6-0.7: Balanced (recommended)
  - 0.4-0.5: Inclusive (more context papers)
- **--num-seeds**: More seeds = better coverage

### Semantic Scholar API Key
Without API key: 100 requests/5 minutes
With API key: 5000 requests/5 minutes

Highly recommended for large explorations!

## 9. Next Steps

### Phase 2: Knowledge Extraction (Coming Soon)
```bash
# Extract structured knowledge using ontologies
python -m src.cli.main extract \
  --papers results.json \
  --ontology config/ontologies/ml_research.yaml \
  --output knowledge_graph.json
```

### Phase 3: Network Analysis (Coming Soon)
```bash
# Find literature gaps and opportunities
python -m src.cli.main analyze \
  --graph knowledge_graph.json \
  --find-gaps \
  --find-opportunities \
  --output analysis.json
```

## 10. Troubleshooting

### "API keys not configured"
→ Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env

### "Rate limit exceeded"
→ Add SEMANTIC_SCHOLAR_API_KEY or reduce --max-papers

### "No papers found"
→ Try broader research question or lower --threshold

### "Import errors"
→ Run: `pip install -r requirements.txt`

## Need Help?

- Check README.md for full documentation
- Review RESEARCH_GRAPH_ARCHITECTURE.md for system design
- Open an issue on GitHub

---

**Happy researching! 🔬**
