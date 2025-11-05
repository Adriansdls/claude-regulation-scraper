# 🧠 Research Graph Explorer: Ultra-Deep Architecture Analysis

## 🎯 Core Problem & Vision

**Goal**: Build a system that achieves **100% recall** for research paper discovery, extracts knowledge using ontologies, and applies network science to find literature gaps, research opportunities, and argument weaknesses.

**Key Insight**: Academic papers form a **citation graph**. Traditional search APIs miss papers. By treating citations as a network and using frontier-based exploration, we can achieve complete coverage of the "giant component" while also discovering "satellite" papers through multi-modal search strategies.

---

## 🏗️ System Architecture: Three-Phase Design

### Phase 1: Paper Discovery Engine (100% Recall)
### Phase 2: Ontology-based Knowledge Extraction
### Phase 3: Network Science & Analysis

---

## 📐 PHASE 1: Paper Discovery Engine - Deep Analysis

### 1.1 The Citation Network Problem

**Papers as a Graph**:
```
Nodes: Research papers
Edges: Citations (directed, A → B means "A cites B")
Problem: Given research question Q, find ALL relevant papers P ⊆ Papers
```

**Key Challenge**:
- APIs like Semantic Scholar only provide **partial coverage**
- Many papers hidden behind paywalls or institutional repositories
- Some papers only discoverable through citations (not keywords)
- "Satellite" papers disconnected from main component

### 1.2 Multi-Strategy Discovery Architecture

#### Strategy 1: Seed-Based Frontier Exploration (Giant Component)

**Algorithm: Intelligent BFS with Relevance Pruning**

```python
# Pseudo-algorithm
frontier = PriorityQueue()  # Priority = relevance_score
visited = Set()
relevant_papers = []

# Step 1: Generate seed papers
seeds = generate_seeds_from_research_question(question)
for seed in seeds:
    frontier.push(seed, priority=1.0)

# Step 2: Frontier exploration
while frontier.not_empty():
    paper = frontier.pop()

    if paper.id in visited:
        continue
    visited.add(paper.id)

    # Get full paper metadata + PDF if possible
    paper_data = multi_source_fetch(paper)

    # LLM-based relevance scoring
    relevance = score_relevance(paper_data, question)

    if relevance > THRESHOLD:
        relevant_papers.append(paper)

        # Expand frontier: backward citations (references)
        for reference in paper.references:
            if reference.id not in visited:
                frontier.push(reference, priority=relevance * 0.9)

        # Expand frontier: forward citations (cited by)
        for citation in paper.cited_by:
            if citation.id not in visited:
                frontier.push(citation, priority=relevance * 0.85)

    # Intelligent stopping criteria
    if should_stop_exploration(frontier, visited, relevant_papers):
        break
```

**Key Design Decisions**:

1. **Priority Queue vs Simple Queue**: Use priority queue weighted by:
   - Parent relevance score (inheritance)
   - Citation count (importance signal)
   - Publication date (recency bias for emerging fields)
   - Author reputation (H-index, citation metrics)

2. **Relevance Scoring with LLMs**:
```python
def score_relevance(paper, question):
    prompt = f"""
    Research Question: {question}

    Paper:
    - Title: {paper.title}
    - Abstract: {paper.abstract}
    - Key findings: {paper.key_findings}

    Score relevance (0-1) and explain:
    1. Does this paper directly address the research question?
    2. Does it provide methodology/background relevant to the question?
    3. Is it a seminal paper in the field?

    Return JSON: {{"relevance": float, "reasoning": str}}
    """
    return llm_call(prompt)
```

3. **Stopping Criteria** (when to stop exploring frontier):
   - Frontier papers consistently score < 0.2 relevance
   - Explored N papers without finding relevant ones (N=50-100)
   - Diminishing returns: new relevant papers/iteration < threshold
   - User-defined max papers limit reached

#### Strategy 2: Satellite Paper Discovery (Beyond Giant Component)

**Problem**: Papers not reachable via citation network from seeds

**Multi-Modal Discovery Approaches**:

1. **Semantic Search Expansion**:
```python
# Extract key concepts from already-found papers
concepts = extract_key_concepts(relevant_papers)

# Generate alternative search queries
search_queries = [
    f"{concept1} AND {concept2}",
    f'"{key_phrase}" methodology',
    f"{domain} {problem_type}"
]

# Search across multiple APIs
for query in search_queries:
    results = parallel_search(
        semantic_scholar=True,
        arxiv=True,
        pubmed=True,
        crossref=True,
        google_scholar=True
    )

    for paper in results:
        if paper not in visited:
            score_and_potentially_add(paper)
```

2. **Author-Based Discovery**:
```python
# Find prolific authors in the field
top_authors = extract_top_authors(relevant_papers)

# Get all their papers in related topics
for author in top_authors:
    author_papers = get_author_papers(author)
    for paper in author_papers:
        if is_similar_topic(paper, research_question):
            score_and_potentially_add(paper)
```

3. **Venue-Based Discovery**:
```python
# Identify key conferences/journals
venues = extract_venues(relevant_papers)

# Get recent papers from these venues
for venue in venues:
    venue_papers = get_venue_papers(venue, years=[2020-2024])
    for paper in venue_papers:
        score_and_potentially_add(paper)
```

4. **Co-Citation Analysis**:
```python
# If papers A and B both cite C, they might be related
for paper_a in relevant_papers:
    for paper_b in relevant_papers:
        if paper_a != paper_b:
            shared_refs = paper_a.refs ∩ paper_b.refs
            if len(shared_refs) > THRESHOLD:
                # Explore papers that cite same sources
                co_cited_papers = find_papers_citing(shared_refs)
                for paper in co_cited_papers:
                    score_and_potentially_add(paper)
```

5. **Bibliographic Coupling**:
```python
# If papers A and B are both cited by C, they might be related
for paper_a in relevant_papers:
    papers_citing_a = get_citations_to(paper_a)
    for citing_paper in papers_citing_a:
        other_cited = citing_paper.references - {paper_a}
        for paper in other_cited:
            score_and_potentially_add(paper)
```

### 1.3 Multi-Source Paper Acquisition

**Hierarchical Source Strategy**:

```python
class PaperFetcher:
    def __init__(self):
        self.sources = [
            SemanticScholarAPI(),  # Best citation data
            ArXivAPI(),            # Preprints, full text
            CrossRefAPI(),         # DOI resolution
            PubMedAPI(),           # Biomedical
            UnpaywallAPI(),        # Open access finder
            GoogleScholarScraper(), # Fallback (with rate limiting)
        ]

    async def fetch_paper(self, paper_id):
        # Try each source in priority order
        for source in self.sources:
            try:
                data = await source.get_paper(paper_id)
                if data:
                    return self.merge_metadata(data)
            except Exception as e:
                continue

        # Fallback: web search for PDF
        return await self.search_web_for_pdf(paper_id)
```

**PDF Acquisition Strategy**:
```python
async def get_pdf(paper):
    # 1. Try ArXiv (if arxiv_id exists)
    if paper.arxiv_id:
        pdf = download_arxiv(paper.arxiv_id)
        if pdf: return pdf

    # 2. Try Unpaywall (open access)
    oa_locations = unpaywall.get_oa_locations(paper.doi)
    for location in oa_locations:
        pdf = download_pdf(location.url)
        if pdf: return pdf

    # 3. Try publisher (if OA)
    if paper.is_open_access:
        pdf = download_from_publisher(paper.url)
        if pdf: return pdf

    # 4. Try institutional repositories
    repo_urls = find_institutional_repos(paper)
    for url in repo_urls:
        pdf = download_pdf(url)
        if pdf: return pdf

    # 5. Try Sci-Hub (ethically questionable, user decides)
    if config.allow_scihub:
        pdf = download_scihub(paper.doi)
        if pdf: return pdf

    return None  # Paper not accessible
```

### 1.4 Text Extraction from PDFs

**Challenge**: PDFs vary wildly in quality (scanned, double-column, equations, figures)

**Multi-Method Extraction**:

```python
class PDFExtractor:
    async def extract_text(pdf_path):
        # Method 1: PyMuPDF (fast, good for text-based PDFs)
        text1 = pymupdf_extract(pdf_path)

        # Method 2: PDFPlumber (better table extraction)
        text2 = pdfplumber_extract(pdf_path)

        # Method 3: If poor quality, use OCR
        if quality_score(text1) < 0.5:
            text3 = ocr_extract(pdf_path)  # Tesseract OCR
            text = choose_best(text1, text2, text3)
        else:
            text = text1

        # Method 4: Structure preservation
        structured = extract_with_structure(pdf_path)
        # sections: {title, abstract, intro, methods, results, discussion, refs}

        return {
            'full_text': text,
            'structured': structured,
            'metadata': extract_metadata(pdf_path)
        }
```

### 1.5 Discovery System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Paper Discovery Orchestrator               │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ Seed Generator│  │ Frontier Explorer │  │ Satellite Finder│
│               │  │                  │  │                 │
│ - LLM Query   │  │ - BFS/DFS        │  │ - Semantic      │
│ - API Search  │  │ - Relevance Score│  │ - Author-based  │
│ - Known Papers│  │ - Smart Stopping │  │ - Venue-based   │
└───────────────┘  └──────────────────┘  └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                  ┌──────────────────┐
                  │ Multi-Source      │
                  │ Paper Fetcher     │
                  │                   │
                  │ - Semantic Scholar│
                  │ - ArXiv           │
                  │ - CrossRef        │
                  │ - PubMed          │
                  │ - Google Scholar  │
                  └──────────────────┘
                             │
                             ▼
                  ┌──────────────────┐
                  │ PDF Acquisition   │
                  │ & Text Extraction │
                  │                   │
                  │ - Open Access     │
                  │ - Repositories    │
                  │ - PyMuPDF/OCR     │
                  └──────────────────┘
                             │
                             ▼
                  ┌──────────────────┐
                  │ Paper Database    │
                  │                   │
                  │ - Metadata        │
                  │ - Full Text       │
                  │ - Citations       │
                  │ - Embeddings      │
                  └──────────────────┘
```

---

## 📊 PHASE 2: Ontology-Based Knowledge Extraction

### 2.1 Ontology Design & Definition

**What is an Ontology in this context?**

An ontology defines:
1. **Entities**: Concepts to extract (e.g., "Method", "Dataset", "Finding", "Limitation")
2. **Relationships**: How entities relate (e.g., "uses", "improves", "contradicts")
3. **Attributes**: Properties of entities (e.g., "accuracy", "dataset_size", "year")

**Example Ontology for Machine Learning Papers**:

```yaml
ontology:
  entities:
    - Method:
        description: "ML algorithm, technique, or approach"
        attributes:
          - name: string
          - category: [supervised, unsupervised, reinforcement]
          - year_introduced: int

    - Dataset:
        description: "Training/evaluation dataset"
        attributes:
          - name: string
          - size: int
          - domain: string

    - Metric:
        description: "Evaluation metric"
        attributes:
          - name: string
          - value: float
          - higher_is_better: bool

    - Finding:
        description: "Key result or claim"
        attributes:
          - claim: string
          - evidence_strength: [strong, moderate, weak]

    - Limitation:
        description: "Acknowledged limitation"
        attributes:
          - description: string
          - severity: [high, medium, low]

  relationships:
    - uses:
        source: Method
        target: Dataset
        description: "Method uses/is evaluated on Dataset"

    - improves:
        source: Method
        target: Method
        description: "Method A improves upon Method B"
        attributes:
          - improvement_percentage: float

    - contradicts:
        source: Finding
        target: Finding
        description: "Finding A contradicts Finding B"

    - addresses:
        source: Method
        target: Limitation
        description: "Method addresses a limitation"
```

### 2.2 LLM-Based Extraction Pipeline

**Key Insight**: Modern LLMs (Claude, GPT-4) can extract structured information with proper prompting

**Extraction Architecture**:

```python
class OntologyExtractor:
    def __init__(self, ontology, llm="claude-3.5-sonnet"):
        self.ontology = ontology
        self.llm = llm

    async def extract_from_paper(self, paper):
        """
        Extract ontology-defined entities and relationships
        """
        # Step 1: Chunk paper into sections
        sections = chunk_paper(paper.text)

        # Step 2: Extract entities per section
        all_entities = {}
        for section_name, section_text in sections.items():
            entities = await self.extract_entities(
                section_text,
                section_name
            )
            all_entities[section_name] = entities

        # Step 3: Extract relationships
        relationships = await self.extract_relationships(
            paper.text,
            all_entities
        )

        # Step 4: Resolve entity references across paper
        resolved_entities = self.resolve_coreferences(all_entities)

        # Step 5: Validate and filter
        validated = self.validate_extractions(
            resolved_entities,
            relationships
        )

        return {
            'entities': validated['entities'],
            'relationships': validated['relationships'],
            'metadata': {
                'paper_id': paper.id,
                'extraction_timestamp': now(),
                'confidence_scores': validated['confidence']
            }
        }
```

**Entity Extraction Prompt Engineering**:

```python
def create_entity_extraction_prompt(text, entity_type, ontology):
    return f"""
You are extracting structured information from a research paper.

ONTOLOGY DEFINITION:
Entity Type: {entity_type.name}
Description: {entity_type.description}
Attributes: {json.dumps(entity_type.attributes, indent=2)}

PAPER TEXT:
{text}

TASK:
Extract ALL instances of {entity_type.name} from the text above.
For each instance, provide:
1. The entity mention (exact text)
2. All required attributes
3. Confidence score (0-1)
4. Supporting evidence (quote from text)

Return as JSON array:
[
  {{
    "mention": "...",
    "attributes": {{...}},
    "confidence": 0.9,
    "evidence": "..."
  }}
]

Important:
- Be exhaustive - extract ALL instances
- If an attribute is not mentioned, use null
- Include context for ambiguous entities
"""
```

**Relationship Extraction**:

```python
async def extract_relationships(self, paper_text, entities):
    """
    Extract relationships between identified entities
    """
    prompt = f"""
You are analyzing relationships between entities in a research paper.

ENTITIES FOUND:
{json.dumps(entities, indent=2)}

RELATIONSHIPS TO EXTRACT:
{json.dumps(self.ontology.relationships, indent=2)}

PAPER TEXT:
{paper_text}

TASK:
For each relationship type, identify ALL instances where entities are related.

Example:
If Method "BERT" uses Dataset "SQuAD":
{{
  "relationship_type": "uses",
  "source": {{"entity_type": "Method", "id": "BERT"}},
  "target": {{"entity_type": "Dataset", "id": "SQuAD"}},
  "confidence": 0.95,
  "evidence": "We evaluate BERT on the SQuAD dataset..."
}}

Return JSON array of all relationships found.
"""

    return await self.llm.complete(prompt)
```

### 2.3 Knowledge Graph Construction

**Multi-Layer Graph Structure**:

```python
class ResearchKnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

        # Layer 1: Paper-level graph (citations)
        self.paper_layer = nx.DiGraph()

        # Layer 2: Concept-level graph (entities & relationships)
        self.concept_layer = nx.MultiDiGraph()

        # Cross-layer connections
        self.paper_to_concepts = {}  # paper_id -> [concept_ids]

    def add_paper(self, paper, extractions):
        """
        Add paper to knowledge graph with extracted concepts
        """
        # Add paper node
        self.paper_layer.add_node(
            paper.id,
            title=paper.title,
            year=paper.year,
            authors=paper.authors,
            venue=paper.venue
        )

        # Add citation edges
        for ref in paper.references:
            self.paper_layer.add_edge(paper.id, ref.id, type='cites')

        # Add extracted entities as nodes
        for entity in extractions['entities']:
            node_id = f"{entity['type']}_{entity['id']}"
            self.concept_layer.add_node(
                node_id,
                type=entity['type'],
                attributes=entity['attributes'],
                mentioned_in=[paper.id]
            )

            # Link paper to concept
            if paper.id not in self.paper_to_concepts:
                self.paper_to_concepts[paper.id] = []
            self.paper_to_concepts[paper.id].append(node_id)

        # Add relationships as edges
        for rel in extractions['relationships']:
            source_id = f"{rel['source']['type']}_{rel['source']['id']}"
            target_id = f"{rel['target']['type']}_{rel['target']['id']}"

            self.concept_layer.add_edge(
                source_id,
                target_id,
                type=rel['type'],
                evidence=rel['evidence'],
                from_paper=paper.id
            )
```

**Graph Storage Options**:

1. **NetworkX** (in-memory, Python-native)
   - Pros: Easy, fast for small-medium graphs (<100k nodes)
   - Cons: Memory constraints, no persistence

2. **Neo4j** (graph database)
   - Pros: Scalable, powerful queries (Cypher), persistent
   - Cons: Requires separate server, learning curve

3. **SQLite + Custom indexes** (lightweight)
   - Pros: Simple, portable, no dependencies
   - Cons: Less efficient for complex graph queries

**Recommendation**: Start with NetworkX, migrate to Neo4j for large-scale

---

## 🔬 PHASE 3: Network Science & Analysis

### 3.1 Literature Gap Detection

**Gap Type 1: Disconnected Concepts**

```python
def find_disconnected_concepts(graph):
    """
    Find pairs of concepts that appear frequently but are never connected
    """
    # Get all concepts and their frequencies
    concept_freq = Counter()
    for paper_id in graph.papers:
        concepts = graph.get_paper_concepts(paper_id)
        concept_freq.update(concepts)

    # Get top N frequent concepts
    top_concepts = [c for c, _ in concept_freq.most_common(50)]

    # Find pairs that SHOULD be connected but aren't
    gaps = []
    for c1 in top_concepts:
        for c2 in top_concepts:
            if c1 < c2:  # Avoid duplicates
                # Are they ever mentioned in same paper?
                co_occurrence = count_co_occurrence(c1, c2, graph)

                # Are they connected via relationship?
                connected = graph.has_relationship(c1, c2)

                if co_occurrence > 5 and not connected:
                    gaps.append({
                        'concept1': c1,
                        'concept2': c2,
                        'co_occurrence': co_occurrence,
                        'gap_type': 'disconnected_frequently_co_occurring'
                    })

    return gaps
```

**Gap Type 2: Under-explored Areas**

```python
def find_underexplored_areas(graph):
    """
    Find topics with high potential but few papers
    """
    # Cluster papers by topic
    clusters = cluster_papers_by_topic(graph)

    underexplored = []
    for cluster_id, papers in clusters.items():
        # Get cluster characteristics
        avg_citations = np.mean([p.citation_count for p in papers])
        recency = np.mean([2024 - p.year for p in papers])
        growth_rate = calculate_growth_rate(papers)

        # High citations + recent + few papers = opportunity
        if avg_citations > 50 and recency < 3 and len(papers) < 20:
            underexplored.append({
                'cluster': cluster_id,
                'topic': describe_cluster(papers),
                'paper_count': len(papers),
                'avg_citations': avg_citations,
                'growth_rate': growth_rate,
                'opportunity_score': calculate_opportunity_score(
                    avg_citations, recency, len(papers), growth_rate
                )
            })

    return sorted(underexplored, key=lambda x: x['opportunity_score'], reverse=True)
```

**Gap Type 3: Missing Methodologies**

```python
def find_missing_methodologies(graph):
    """
    Find methods that work for Problem A but haven't been tried for similar Problem B
    """
    # Get all (method, problem) pairs
    method_problem_pairs = graph.get_method_problem_pairs()

    # Cluster problems by similarity
    problem_clusters = cluster_problems_by_similarity(
        graph.get_all_problems()
    )

    missing = []
    for cluster in problem_clusters:
        # What methods are used in this cluster?
        methods_used = set()
        for problem in cluster:
            methods = graph.get_methods_for_problem(problem)
            methods_used.update(methods)

        # What methods are used in SIMILAR clusters but not this one?
        similar_clusters = get_similar_clusters(cluster, problem_clusters)
        for similar_cluster in similar_clusters:
            for problem in similar_cluster:
                methods = graph.get_methods_for_problem(problem)
                for method in methods:
                    if method not in methods_used:
                        missing.append({
                            'method': method,
                            'current_problems': list(similar_cluster),
                            'potential_problem': cluster,
                            'rationale': f"{method} works for {similar_cluster} but not tried for {cluster}"
                        })

    return missing
```

### 3.2 Echo Chamber & Citation Ring Detection

**Echo Chamber**: Group of papers that cite each other disproportionately

```python
def detect_echo_chambers(graph, min_size=5):
    """
    Find strongly connected components with high internal citation density
    """
    # Find strongly connected components
    sccs = list(nx.strongly_connected_components(graph.paper_layer))

    echo_chambers = []
    for scc in sccs:
        if len(scc) < min_size:
            continue

        # Calculate internal vs external citation ratio
        internal_citations = count_internal_citations(scc, graph)
        external_citations = count_external_citations(scc, graph)

        ratio = internal_citations / (external_citations + 1)

        # Calculate citation diversity
        diversity = calculate_citation_diversity(scc, graph)

        if ratio > 3.0 and diversity < 0.3:  # Suspicious
            echo_chambers.append({
                'papers': list(scc),
                'size': len(scc),
                'internal_external_ratio': ratio,
                'diversity_score': diversity,
                'authors': get_unique_authors(scc, graph),
                'venues': get_venues(scc, graph)
            })

    return echo_chambers
```

**Citation Ring Detection**:

```python
def detect_citation_rings(graph, max_ring_size=10):
    """
    Find small cycles where papers cite each other in a ring
    """
    rings = []

    # Find all cycles up to max_ring_size
    for cycle in nx.simple_cycles(graph.paper_layer):
        if 3 <= len(cycle) <= max_ring_size:
            # Analyze the cycle
            papers = [graph.get_paper(p) for p in cycle]

            # Are they by same authors?
            author_overlap = calculate_author_overlap(papers)

            # Do they have legitimate scientific relationship?
            content_similarity = calculate_content_similarity(papers)

            # Are citation reasons substantive?
            citation_quality = analyze_citation_contexts(cycle, graph)

            if author_overlap > 0.6 or citation_quality < 0.4:
                rings.append({
                    'cycle': cycle,
                    'size': len(cycle),
                    'author_overlap': author_overlap,
                    'content_similarity': content_similarity,
                    'citation_quality': citation_quality,
                    'suspicion_score': calculate_suspicion(
                        author_overlap, citation_quality
                    )
                })

    return sorted(rings, key=lambda x: x['suspicion_score'], reverse=True)
```

### 3.3 Argument Weakness Detection

**Cascading Citations**: A cites B cites C, but A doesn't verify C

```python
def find_cascading_citations(graph):
    """
    Find chains where papers cite indirectly without verification
    """
    cascades = []

    for paper_a in graph.papers:
        refs_a = graph.get_references(paper_a)

        for paper_b in refs_a:
            refs_b = graph.get_references(paper_b)

            # Does A cite claims originally from B's references?
            for paper_c in refs_b:
                # Check if A mentions concepts from C
                concepts_c = graph.get_paper_concepts(paper_c)
                concepts_mentioned_in_a = graph.get_paper_concepts(paper_a)

                overlap = set(concepts_c) & set(concepts_mentioned_in_a)

                if overlap and paper_c not in refs_a:
                    # A uses concepts from C but only cites B
                    cascades.append({
                        'paper': paper_a,
                        'intermediate': paper_b,
                        'original_source': paper_c,
                        'concepts': list(overlap),
                        'chain_length': 2,
                        'risk': 'high' if len(overlap) > 3 else 'medium'
                    })

    return cascades
```

**Weak Empirical Support**:

```python
def find_weakly_supported_claims(graph):
    """
    Find highly cited papers with weak empirical evidence
    """
    weak_claims = []

    for paper in graph.papers:
        if paper.citation_count < 50:  # Only check influential papers
            continue

        # Extract claims and their evidence
        extractions = graph.get_extractions(paper)
        findings = [e for e in extractions if e['type'] == 'Finding']

        for finding in findings:
            # Analyze evidence strength
            evidence_strength = finding.get('evidence_strength', 'unknown')

            # How many papers cite this specific finding?
            citing_papers = graph.get_papers_citing_finding(
                paper.id,
                finding['id']
            )

            if len(citing_papers) > 10 and evidence_strength == 'weak':
                weak_claims.append({
                    'paper': paper,
                    'finding': finding,
                    'citation_count': len(citing_papers),
                    'evidence_strength': evidence_strength,
                    'risk_score': len(citing_papers) * (1 if evidence_strength == 'weak' else 0.5)
                })

    return sorted(weak_claims, key=lambda x: x['risk_score'], reverse=True)
```

### 3.4 Research Opportunity Identification

**Betweenness Centrality for Bridges**:

```python
def find_interdisciplinary_opportunities(graph):
    """
    Find concepts that bridge different research areas (high betweenness)
    """
    # Calculate betweenness centrality for all concept nodes
    betweenness = nx.betweenness_centrality(graph.concept_layer)

    # Find high-betweenness concepts with few papers
    opportunities = []
    for concept, centrality in betweenness.items():
        if centrality > 0.1:  # High betweenness
            papers = graph.get_papers_mentioning(concept)
            if len(papers) < 10:  # Few papers
                communities = graph.get_communities_connected_by(concept)
                opportunities.append({
                    'concept': concept,
                    'betweenness': centrality,
                    'paper_count': len(papers),
                    'bridges_communities': communities,
                    'opportunity_type': 'interdisciplinary_bridge',
                    'description': f"{concept} connects {len(communities)} research areas but is understudied"
                })

    return opportunities
```

**Temporal Analysis for Emerging Trends**:

```python
def find_emerging_trends(graph):
    """
    Find rapidly growing research areas
    """
    # Group papers by concept and year
    concept_timeline = defaultdict(lambda: defaultdict(int))

    for paper in graph.papers:
        year = paper.year
        concepts = graph.get_paper_concepts(paper.id)
        for concept in concepts:
            concept_timeline[concept][year] += 1

    # Calculate growth rates
    trends = []
    for concept, timeline in concept_timeline.items():
        years = sorted(timeline.keys())
        if len(years) < 3:
            continue

        # Fit exponential growth model
        growth_rate = calculate_growth_rate(timeline)

        # Recent acceleration?
        recent_years = [y for y in years if y >= 2022]
        recent_growth = sum(timeline[y] for y in recent_years) / len(recent_years) if recent_years else 0
        older_years = [y for y in years if y < 2022]
        older_growth = sum(timeline[y] for y in older_years) / len(older_years) if older_years else 0

        acceleration = recent_growth / (older_growth + 1)

        if growth_rate > 0.2 and acceleration > 2.0:
            trends.append({
                'concept': concept,
                'growth_rate': growth_rate,
                'acceleration': acceleration,
                'total_papers': sum(timeline.values()),
                'trend_type': 'emerging',
                'forecast': forecast_future_growth(timeline)
            })

    return sorted(trends, key=lambda x: x['growth_rate'] * x['acceleration'], reverse=True)
```

---

## 🛠️ Technology Stack Recommendations

### Core Infrastructure

```yaml
Language: Python 3.10+

LLM Integration:
  Primary: Anthropic Claude 3.5 Sonnet (long context, structured extraction)
  Fallback: OpenAI GPT-4o (for comparison)
  Embedding: OpenAI text-embedding-3-large or Voyage AI

Paper Discovery APIs:
  - Semantic Scholar API (primary - best citation data)
  - arXiv API (preprints)
  - CrossRef API (DOI resolution)
  - PubMed Central API (biomedical papers)
  - OpenAlex API (open scholarly data)

PDF Processing:
  - PyMuPDF (fast, text extraction)
  - PDFPlumber (tables and structure)
  - Tesseract OCR (scanned documents)
  - GROBID (academic PDF parsing)

Graph Processing:
  Small-scale (<100k papers): NetworkX
  Large-scale (>100k papers): Neo4j

Storage:
  Metadata: PostgreSQL
  Full text: Object storage (S3, local filesystem)
  Graph: Neo4j or NetworkX pickles
  Cache: Redis

Task Queue:
  - Celery + Redis (distributed processing)
  - For paper fetching, PDF processing, extraction

Web Scraping (when needed):
  - Playwright (JavaScript-heavy sites)
  - Beautiful Soup (static HTML)
  - Scrapy (large-scale scraping)

Embeddings & Similarity:
  - Sentence-BERT for semantic similarity
  - Voyage AI for academic embeddings

Network Analysis:
  - NetworkX (algorithms)
  - python-igraph (faster for large graphs)
  - Gephi export for visualization

Monitoring & Observability:
  - Logging: structlog
  - Metrics: Prometheus
  - Tracing: Langfuse/LangSmith (LLM calls)
```

### Project Structure

```
research-graph-explorer/
│
├── README.md
├── pyproject.toml
├── .env
│
├── config/
│   ├── ontologies/          # User-defined ontology schemas
│   │   ├── ml_research.yaml
│   │   └── biology.yaml
│   └── settings.yaml        # App configuration
│
├── src/
│   ├── discovery/           # Phase 1: Paper Discovery
│   │   ├── seed_generator.py
│   │   ├── frontier_explorer.py
│   │   ├── relevance_scorer.py
│   │   ├── satellite_finder.py
│   │   ├── paper_fetcher.py       # Multi-source API client
│   │   └── pdf_processor.py       # PDF acquisition & extraction
│   │
│   ├── extraction/          # Phase 2: Knowledge Extraction
│   │   ├── ontology_manager.py    # Load and validate ontologies
│   │   ├── entity_extractor.py    # LLM-based entity extraction
│   │   ├── relation_extractor.py  # Relationship extraction
│   │   └── knowledge_graph.py     # Graph construction
│   │
│   ├── analysis/            # Phase 3: Network Science
│   │   ├── gap_detector.py
│   │   ├── echo_chamber_detector.py
│   │   ├── opportunity_finder.py
│   │   ├── argument_analyzer.py
│   │   └── network_metrics.py
│   │
│   ├── models/              # Data models
│   │   ├── paper.py
│   │   ├── citation.py
│   │   ├── ontology.py
│   │   └── extraction.py
│   │
│   ├── infrastructure/      # Core infrastructure
│   │   ├── database.py      # DB connections
│   │   ├── cache.py         # Redis caching
│   │   ├── queue.py         # Celery tasks
│   │   └── llm_client.py    # LLM abstraction
│   │
│   ├── utils/
│   │   ├── text_processing.py
│   │   ├── embeddings.py
│   │   └── graph_utils.py
│   │
│   └── api/                 # REST API (optional)
│       └── routes.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── notebooks/               # Jupyter notebooks for analysis
│   └── exploratory_analysis.ipynb
│
├── cli/                     # Command-line interface
│   └── main.py
│
├── data/                    # Local data storage
│   ├── papers/
│   ├── graphs/
│   └── cache/
│
└── scripts/                 # Utility scripts
    ├── setup_db.py
    └── import_ontology.py
```

---

## 🚀 Implementation Phases

### Phase 0: Foundation (Week 1-2)

- [ ] Set up project structure
- [ ] Configure API clients (Semantic Scholar, arXiv, etc.)
- [ ] Implement basic Paper model and storage
- [ ] Set up database schema
- [ ] Implement caching layer
- [ ] Create CLI skeleton

### Phase 1: Discovery MVP (Week 3-6)

- [ ] Implement seed generation from research question
- [ ] Build frontier-based BFS explorer
- [ ] Integrate Semantic Scholar API
- [ ] Implement LLM relevance scoring
- [ ] Add PDF downloading (ArXiv, Unpaywall)
- [ ] Basic text extraction from PDFs
- [ ] Store papers in database
- [ ] Test on 100-paper dataset

**Milestone**: Given research question, discover and store 100+ relevant papers

### Phase 2: Discovery Enhancement (Week 7-10)

- [ ] Add satellite paper discovery (semantic search)
- [ ] Implement author-based discovery
- [ ] Add venue-based discovery
- [ ] Improve PDF acquisition (multiple sources)
- [ ] Enhanced text extraction (OCR, structure)
- [ ] Implement stopping criteria
- [ ] Add provenance tracking
- [ ] Test on 1000-paper dataset

**Milestone**: Achieve >90% recall on known research questions

### Phase 3: Extraction MVP (Week 11-14)

- [ ] Design ontology schema format
- [ ] Implement ontology loader/validator
- [ ] Build entity extraction with LLMs
- [ ] Build relationship extraction
- [ ] Create basic knowledge graph structure
- [ ] Store extractions in database
- [ ] Implement coreference resolution
- [ ] Test extraction quality on 100 papers

**Milestone**: Extract entities/relationships from papers into graph

### Phase 4: Extraction Enhancement (Week 15-18)

- [ ] Improve extraction prompts
- [ ] Add multi-turn extraction for complex entities
- [ ] Implement extraction validation
- [ ] Build entity linking (merge duplicates)
- [ ] Add confidence scoring
- [ ] Support multiple ontologies
- [ ] Create extraction UI for refinement
- [ ] Scale to 1000-paper extraction

**Milestone**: High-quality knowledge graph from 1000+ papers

### Phase 5: Analysis MVP (Week 19-22)

- [ ] Implement basic graph metrics
- [ ] Build gap detection algorithms
- [ ] Create echo chamber detector
- [ ] Add cascading citation finder
- [ ] Implement opportunity identification
- [ ] Generate analysis reports
- [ ] Create visualization exports (Gephi)
- [ ] Test on real research questions

**Milestone**: Identify literature gaps and research opportunities

### Phase 6: Analysis Enhancement (Week 23-26)

- [ ] Advanced network algorithms
- [ ] Temporal analysis (trends over time)
- [ ] Argument weakness detection
- [ ] Interdisciplinary bridge finding
- [ ] Custom analysis plugins
- [ ] Interactive visualization
- [ ] Export analysis to reports
- [ ] User feedback loop

**Milestone**: Production-ready analysis system

### Phase 7: Production (Week 27-30)

- [ ] Performance optimization
- [ ] Horizontal scaling
- [ ] Web UI (optional)
- [ ] API endpoints
- [ ] Documentation
- [ ] User testing
- [ ] Bug fixes
- [ ] Deployment

---

## ⚠️ Critical Challenges & Solutions

### Challenge 1: API Rate Limits

**Problem**: Semantic Scholar, arXiv, etc. have rate limits

**Solutions**:
- Implement exponential backoff
- Use multiple API keys (if allowed)
- Cache aggressively (Redis)
- Batch requests
- Implement request queuing with Celery
- Respect robots.txt and be a good citizen

### Challenge 2: PDF Access (Paywalls)

**Problem**: Many papers behind paywalls

**Solutions**:
- Prioritize open access (Unpaywall API)
- Use institutional access (if available)
- Focus on preprints (arXiv)
- Metadata-only analysis when PDF unavailable
- Sci-Hub (user decides ethically)

### Challenge 3: LLM Costs

**Problem**: Processing 1000s of papers is expensive

**Solutions**:
- Use smaller models for screening (GPT-4o-mini)
- Use larger models only for final extraction (Claude 3.5)
- Cache extraction results
- Process abstracts first, full text only if relevant
- Batch processing
- Use local models (Llama 3) for some tasks

### Challenge 4: Extraction Quality

**Problem**: LLMs can hallucinate entities/relationships

**Solutions**:
- Multi-stage verification
- Confidence scoring
- Evidence quotes (always include source text)
- Human-in-the-loop for ambiguous cases
- Cross-validation (multiple papers same concept)
- Fact-checking against source text

### Challenge 5: Graph Scalability

**Problem**: 10k+ papers = millions of nodes/edges

**Solutions**:
- Use Neo4j for large graphs
- Implement graph partitioning
- Progressive loading (load subgraphs on demand)
- Use igraph for compute-heavy algorithms
- Pre-compute common metrics
- Export subgraphs for visualization

### Challenge 6: Ontology Design

**Problem**: Hard to design good ontologies upfront

**Solutions**:
- Iterative ontology refinement
- Learn from extracted data
- Use LLM to suggest entity/relationship types
- Start simple, expand later
- Support multiple ontologies
- Allow user customization

---

## 🎯 Novel Approaches & Innovations

### Innovation 1: Hybrid Discovery (API + Network Traversal)

Traditional: Use API search only → miss papers
Our approach: API for seeds → network traversal → satellite search

### Innovation 2: LLM-Powered Relevance Scoring

Traditional: Keyword matching, TF-IDF
Our approach: LLM reads abstract, scores relevance to research question with reasoning

### Innovation 3: Multi-Layer Knowledge Graph

Traditional: Just citation network
Our approach: Paper layer + concept layer + extraction layer = rich analysis

### Innovation 4: Argument Weakness Detection

Traditional: Citation count as proxy for quality
Our approach: Analyze citation chains, evidence strength, echo chambers

### Innovation 5: Dynamic Ontologies

Traditional: Fixed schema
Our approach: User-defined, LLM-suggested, iteratively refined

### Innovation 6: Provenance Tracking

Traditional: Just store results
Our approach: Track how each paper was discovered, why it's relevant, evidence trail

---

## 🎨 Recommendation: New Repository vs Current Repo

**Recommendation: CREATE NEW REPOSITORY**

### Reasoning:

1. **Completely Different Domain**:
   - Current: Regulatory compliance monitoring
   - New: Academic research paper analysis
   - Minimal code reuse opportunity

2. **Different Dependencies**:
   - Current: Firecrawl, regulation-specific APIs
   - New: Semantic Scholar, arXiv, graph databases
   - Would bloat current repo

3. **Different Users & Use Cases**:
   - Current: Compliance professionals
   - New: Researchers, academics
   - Different documentation, examples, workflows

4. **Scaling & Architecture**:
   - New system much more complex (3 phases, graph DBs, etc.)
   - Separate concerns = better maintainability

5. **Future Independent Evolution**:
   - Each system can evolve independently
   - Easier to onboard contributors
   - Cleaner git history

### What to Reuse (Lessons, Not Code):

- Agent architecture patterns
- LLM integration best practices
- CLI design (Click + Rich)
- Configuration management approach
- Testing patterns

### Suggested Repository Name:

`research-graph-explorer` or `scholar-network-analyzer` or `literature-discovery-engine`

---

## 📈 Success Metrics

### Phase 1 (Discovery):
- **Recall**: >95% of relevant papers found (vs human expert)
- **Precision**: >80% of discovered papers are relevant
- **Coverage**: Discover papers across all major APIs
- **Speed**: <30 seconds per paper fetch

### Phase 2 (Extraction):
- **Entity extraction F1**: >0.85
- **Relationship extraction F1**: >0.75
- **Extraction completeness**: >90% of key entities extracted
- **Processing speed**: <5 minutes per paper

### Phase 3 (Analysis):
- **Gap detection accuracy**: >80% of identified gaps confirmed by experts
- **Echo chamber detection precision**: >90%
- **Opportunity relevance**: >70% rated as valuable by researchers
- **Analysis speed**: <10 seconds for 1000-paper graph

---

## 🌟 Future Enhancements (Post-MVP)

1. **Real-time Monitoring**: Track new papers as they're published
2. **Collaborative Ontologies**: Share ontologies with community
3. **Automated Literature Review**: Generate review papers from graph
4. **Citation Recommendation**: Suggest papers to cite based on graph
5. **Cross-Domain Discovery**: Find analogies across fields
6. **Author Network Analysis**: Collaboration recommendations
7. **Funding Opportunity Matching**: Match gaps to grant calls
8. **Peer Review Assist**: Flag potential conflicts, missing citations
9. **Knowledge Base Integration**: Link to Wikipedia, Wikidata
10. **Multilingual Support**: Non-English papers

---

## 🎬 Next Steps

1. **Review & Feedback**: Get user feedback on this architecture
2. **Create New Repository**: Initialize with structure above
3. **Spike: API Testing**: Test Semantic Scholar, arXiv APIs (2 hours)
4. **Spike: LLM Extraction**: Test entity extraction quality (4 hours)
5. **Spike: Graph Storage**: Compare NetworkX vs Neo4j (2 hours)
6. **Define MVP Scope**: Choose specific research domain for MVP
7. **Create Detailed Tasks**: Break Phase 0-1 into granular tasks
8. **Start Development**: Begin with foundation (APIs, models, storage)

---

## 📚 References for Implementation

### Academic Papers on This Topic:
- "Citation Recommendation: A Survey" (Färber & Jatowt, 2020)
- "Automated Knowledge Base Construction" (Wang et al., 2021)
- "Literature-based Discovery" (Swanson, 1986)
- "Scientific Paper Mining" (Ammar et al., 2018)

### Useful Tools/Datasets:
- Semantic Scholar API: https://api.semanticscholar.org/
- OpenAlex: https://openalex.org/
- CORD-19 dataset (example of paper analysis)
- Paperscape (visualization inspiration)

---

**This architecture provides a solid foundation for 100% recall paper discovery with network science analysis. Ready to build?**
