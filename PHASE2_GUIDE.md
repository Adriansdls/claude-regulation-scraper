# 📚 Phase 2: Knowledge Extraction Guide

Complete guide to using Phase 2 features for extracting structured knowledge from research papers.

---

## 🎯 What is Phase 2?

Phase 2 takes discovered papers and extracts structured knowledge using **ontologies**:

```
Papers (JSON) → Phase 2 → Knowledge Graph
                    ↓
        1. Download PDFs
        2. Extract Text
        3. Parse Sections
        4. Extract Entities
        5. Extract Relationships
        6. Build Knowledge Graph
```

**Result**: A multi-layer knowledge graph with:
- Paper citation network
- Extracted entities (methods, datasets, findings, etc.)
- Relationships between entities
- Provenance (which paper, which section)

---

## 🚀 Quick Start

### 1. Run Phase 1 First (Discovery)

```bash
python -m src.cli.main discover \
  "What are recent advances in graph neural networks?" \
  --max-papers 50 \
  --output gnn_papers.json
```

### 2. Extract Knowledge

```bash
python -m src.cli.main extract gnn_papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output gnn_knowledge_graph.json \
  --max-papers 20
```

**What happens**:
1. ✅ Loads 50 discovered papers
2. ✅ Downloads PDFs (arXiv, Unpaywall, DOI)
3. ✅ Extracts text with PyMuPDF/pdfplumber
4. ✅ Parses into sections (abstract, intro, methods, etc.)
5. ✅ Extracts entities using LLM (Method, Dataset, Metric, etc.)
6. ✅ Extracts relationships (uses, improves, evaluates_on, etc.)
7. ✅ Builds knowledge graph
8. ✅ Exports for Gephi visualization

### 3. Results

**Console output**:
- Progress for each phase
- Statistics (PDFs downloaded, text extracted, entities found)
- Final graph statistics

**Output files**:
- `gnn_knowledge_graph.json` - Full knowledge graph with all data
- `gnn_knowledge_graph_gephi/` - Gephi-compatible files for visualization

---

## 📐 Ontologies

### What is an Ontology?

An ontology defines what to extract:
- **Entity Types**: Things to find (Method, Dataset, Finding, etc.)
- **Relationship Types**: Connections (uses, improves, contradicts, etc.)
- **Attributes**: Properties of entities (name, year, accuracy, etc.)

### Example Ontology (ML Research)

```yaml
name: "ML Research Ontology"
description: "For machine learning papers"
domain: "machine_learning"

entity_types:
  - name: "Method"
    description: "ML algorithm or technique"
    attributes:
      name: string
      category: string
      year_introduced: int
    examples:
      - "BERT"
      - "ResNet"
      - "GPT-3"

  - name: "Dataset"
    description: "Training or evaluation dataset"
    attributes:
      name: string
      size: int
    examples:
      - "ImageNet"
      - "SQuAD"

relationship_types:
  - name: "uses"
    description: "Method uses Dataset"
    source_types: ["Method"]
    target_types: ["Dataset"]

  - name: "improves"
    description: "Method A improves Method B"
    source_types: ["Method"]
    target_types: ["Method"]
```

### Using the Built-in Ontology

```bash
# ML Research ontology (included)
python -m src.cli.main extract papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output kg.json
```

### Creating Custom Ontologies

Create `my_ontology.yaml`:

```yaml
name: "Biology Research"
description: "For biology papers"
domain: "biology"
version: "1.0.0"

entity_types:
  - name: "Protein"
    description: "Protein or gene"
    attributes:
      name: string
      function: string
    examples:
      - "p53 tumor suppressor"
      - "BRCA1"

  - name: "Disease"
    description: "Disease or condition"
    attributes:
      name: string
    examples:
      - "Alzheimer's disease"
      - "Type 2 diabetes"

relationship_types:
  - name: "associated_with"
    description: "Protein associated with Disease"
    source_types: ["Protein"]
    target_types: ["Disease"]
```

Then use it:

```bash
python -m src.cli.main extract biology_papers.json \
  --ontology my_ontology.yaml \
  --output biology_kg.json
```

---

## 🔧 Advanced Options

### Download PDFs Only (No Extraction)

```bash
python -m src.cli.main extract papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output kg.json \
  --no-download-pdfs  # Skip PDF download
```

### Limit Number of Papers

```bash
# Extract from first 10 papers only
python -m src.cli.main extract papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output kg.json \
  --max-papers 10
```

---

## 📊 Output Format

### Knowledge Graph JSON

```json
{
  "ontology": {
    "name": "ML Research Ontology",
    "entity_types": [...],
    "relationship_types": [...]
  },
  "papers": {
    "paper_id_1": {
      "title": "...",
      "authors": [...],
      "has_pdf": true,
      "text_extracted": true
    }
  },
  "entities": {
    "entity_id_1": {
      "entity_type": "Method",
      "text": "BERT",
      "attributes": {"name": "BERT", "category": "transformer"},
      "source_paper_id": "paper_id_1",
      "source_section": "introduction",
      "confidence": 0.95
    }
  },
  "relationships": {
    "rel_id_1": {
      "relationship_type": "uses",
      "source_entity_id": "entity_id_1",
      "target_entity_id": "entity_id_2",
      "evidence": "BERT was trained on the SQuAD dataset",
      "confidence": 0.88
    }
  },
  "statistics": {
    "papers": {"total_papers": 20},
    "entities": {
      "total_entities": 156,
      "by_type": {"Method": 45, "Dataset": 28, "Metric": 83}
    },
    "relationships": {
      "total_relationships": 89,
      "by_type": {"uses": 34, "improves": 28, "achieves": 27}
    }
  }
}
```

---

## 🎨 Visualization

### Gephi Export

The system automatically exports Gephi-compatible files:

```
knowledge_graph_gephi/
├── concept_graph.gexf  # Entity relationship network
└── paper_graph.gexf    # Paper citation network
```

**To visualize**:
1. Download [Gephi](https://gephi.org/)
2. Open Gephi
3. File → Open → Select `.gexf` file
4. Apply layout (ForceAtlas 2 recommended)
5. Explore your knowledge graph!

### Python Visualization

```python
from src.extraction.knowledge_graph import KnowledgeGraph

# Load graph
kg = KnowledgeGraph.load("knowledge_graph.json")

# Get statistics
stats = kg.get_statistics()
print(stats)

# Get entities of specific type
methods = [e for e in kg.entities.values() if e.entity_type == "Method"]

# Get relationships for an entity
entity_id = list(kg.entities.keys())[0]
relationships = kg.get_entity_relationships(entity_id)
```

---

## 🔬 How It Works

### PDF Acquisition Strategy

1. **Check cache**: Already downloaded?
2. **Try arXiv**: If arXiv ID exists
3. **Try OpenAccess URL**: From Semantic Scholar metadata
4. **Try Unpaywall API**: Find open access versions
5. **Try DOI resolution**: Resolve DOI to PDF

### Text Extraction Strategy

1. **Try PyMuPDF**: Fast, works for most PDFs
2. **Try pdfplumber**: Better for tables/structure
3. **Quality assessment**: Check extraction quality
4. **Best result**: Return highest quality extraction

### Entity Extraction (LangExtract + LLM)

For each entity type:
1. **Prepare prompt**: Include entity description, examples, attributes
2. **LLM extraction**: Use Claude/GPT-4 to find entities
3. **Parse response**: Extract entities with attributes
4. **Add provenance**: Track source paper and section
5. **Confidence scoring**: Assign confidence scores

### Relationship Extraction

1. **Group entities**: By type for matching
2. **For each relationship type**: Find valid source/target pairs
3. **LLM matching**: Ask LLM to identify relationships
4. **Extract evidence**: Get supporting quotes
5. **Build graph**: Add relationships to knowledge graph

### Post-Processing

1. **Entity linking**: Merge similar entities (optional)
2. **Validation**: Check extraction quality
3. **Statistics**: Compute comprehensive stats

---

## 💡 Tips for Better Extraction

### 1. Design Good Ontologies

**✅ Good entity type**:
```yaml
- name: "Method"
  description: "Machine learning algorithm or technique"
  attributes:
    name: string
    category: string
  examples:
    - "BERT (Bidirectional Encoder...)"
    - "ResNet (Residual Neural Networks)"
```

**❌ Too vague**:
```yaml
- name: "Thing"
  description: "Any concept"
  examples: []
```

### 2. Provide Examples

More examples = better extraction accuracy:
- 3-5 examples per entity type
- Include full names and abbreviations
- Show variety

### 3. Limit Papers for Testing

Start small to test ontology:
```bash
--max-papers 5  # Test on 5 papers first
```

Then scale up:
```bash
--max-papers 50  # Full extraction
```

### 4. Check PDF Quality

Not all papers have accessible PDFs. Phase 2 handles this gracefully:
- Attempts multiple sources
- Falls back to metadata-only if no PDF
- Reports statistics on success rate

---

## 🐛 Troubleshooting

### "No PDFs downloaded"

→ Many papers are behind paywalls. Try:
- Papers with arXiv IDs (always open access)
- Recent papers (more likely to have PDFs)
- Open access venues

### "Low quality text extraction"

→ Some PDFs are scanned images. Solution:
- Use papers with text-based PDFs
- Future: OCR support (Phase 2.5)

### "Few entities extracted"

→ Check:
- Ontology examples are clear
- Entity descriptions are specific
- Papers actually contain those concepts

### "Extraction is slow"

→ Normal! Processing:
- 20 papers takes ~15-30 minutes
- Includes: PDF download + text extraction + LLM calls
- Use `--max-papers 10` for faster testing

---

## 📈 Next Steps

After Phase 2, you have a knowledge graph. Next:

### Phase 3: Analysis (Coming Soon)

```bash
python -m src.cli.main analyze knowledge_graph.json \
  --find-gaps \
  --find-opportunities \
  --detect-echo-chambers \
  --output analysis.json
```

Will provide:
- Literature gaps (missing connections)
- Research opportunities (high-impact areas)
- Echo chambers (self-citing groups)
- Emerging trends (growing topics)

### Custom Analysis

```python
from src.extraction.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph.load("knowledge_graph.json")

# Find most cited methods
methods = [e for e in kg.entities.values() if e.entity_type == "Method"]
method_citations = {m: len(kg.get_concept_papers(m.entity_id)) for m in methods}
top_methods = sorted(method_citations.items(), key=lambda x: x[1], reverse=True)[:10]

# Find methods without datasets
methods_without_data = []
for method in methods:
    rels = kg.get_entity_relationships(method.entity_id, direction="outgoing")
    has_dataset = any(r.relationship_type == "uses" for r in rels)
    if not has_dataset:
        methods_without_data.append(method)

# Identify gaps!
print(f"Methods without evaluation datasets: {len(methods_without_data)}")
```

---

## 🎓 Examples

### Example 1: NLP Research

```bash
# Discover
python -m src.cli.main discover \
  "What are the best methods for few-shot learning in NLP?" \
  --max-papers 30 \
  --output nlp_papers.json

# Extract
python -m src.cli.main extract nlp_papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output nlp_kg.json \
  --max-papers 15
```

**Result**: Graph showing:
- Methods (GPT-3, BERT, T5, etc.)
- Datasets (GLUE, SuperGLUE, SQuAD, etc.)
- Metrics (Accuracy, F1, Perplexity, etc.)
- Relationships (GPT-3 uses SQuAD, achieves 95% accuracy, etc.)

### Example 2: Computer Vision

```bash
# Discover
python -m src.cli.main discover \
  "How have vision transformers improved over CNNs?" \
  --max-papers 40 \
  --output vision_papers.json

# Extract
python -m src.cli.main extract vision_papers.json \
  --ontology config/ontologies/ml_research.yaml \
  --output vision_kg.json
```

**Result**: Graph comparing:
- Traditional CNNs (ResNet, VGG, etc.)
- Vision Transformers (ViT, Swin, DeiT, etc.)
- Performance improvements
- Datasets used

---

**Phase 2 gives you structured knowledge ready for analysis. Build your knowledge graph today! 🚀**
