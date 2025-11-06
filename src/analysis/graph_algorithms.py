"""Core graph analysis algorithms for network science.

This module provides pre-defined, optimized graph algorithms for common
network science operations. These are fast, tested, and safe.

For custom analyses, see dynamic_executor.py which allows LLM-generated
NetworkX code execution in a sandbox.
"""

import networkx as nx
from typing import Dict, List, Tuple, Any, Optional, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
import numpy as np

try:
    import community as community_louvain  # python-louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False

try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False


@dataclass
class CommunityResult:
    """Result from community detection"""
    algorithm: str
    num_communities: int
    modularity: float
    communities: Dict[str, int]  # node_id -> community_id
    community_sizes: Dict[int, int]  # community_id -> size
    largest_community_size: int


@dataclass
class CentralityResult:
    """Result from centrality calculation"""
    metric: str
    top_nodes: List[Tuple[str, float]]  # (node_id, score)
    mean_score: float
    median_score: float
    max_score: float


@dataclass
class GapResult:
    """Result from gap detection"""
    gap_type: str
    entity_id: Optional[str]
    entity_text: Optional[str]
    importance_score: float
    connections: int
    reason: str
    related_entities: List[str]
    evidence: Dict[str, Any]


@dataclass
class EchoChamberResult:
    """Result from echo chamber detection"""
    cluster_id: int
    size: int
    node_ids: List[str]
    node_titles: List[str]  # Sample titles
    internal_citations: int
    external_citations: int
    internal_ratio: float
    suspicion_score: float  # 0-1, higher = more suspicious
    reason: str


class GraphAnalyzer:
    """
    Core graph analysis functionality.

    Provides pre-defined, optimized algorithms for common network science operations.
    All methods are tested, safe, and performant.

    For custom analyses beyond these methods, use DynamicGraphQueryExecutor.
    """

    def __init__(self, knowledge_graph):
        """
        Initialize analyzer with a knowledge graph.

        Args:
            knowledge_graph: KnowledgeGraph instance from Phase 2
        """
        self.kg = knowledge_graph

    # ========================================================================
    # COMMUNITY DETECTION
    # ========================================================================

    def detect_communities(
        self,
        layer: str = "paper",
        algorithm: str = "louvain",
        resolution: float = 1.0,
        min_community_size: int = 2
    ) -> CommunityResult:
        """
        Detect communities (clusters) in the network.

        Communities are groups of nodes that are more densely connected
        to each other than to the rest of the network.

        Args:
            layer: "paper" (citation network) or "concept" (entity network)
            algorithm: "louvain" (fast), "leiden" (accurate), "label_propagation" (simple)
            resolution: Higher values = more smaller communities
            min_community_size: Filter out communities smaller than this

        Returns:
            CommunityResult with community assignments and statistics
        """
        graph = self.kg.paper_graph if layer == "paper" else self.kg.concept_graph

        if graph.number_of_nodes() == 0:
            return CommunityResult(
                algorithm=algorithm,
                num_communities=0,
                modularity=0.0,
                communities={},
                community_sizes={},
                largest_community_size=0
            )

        # Convert to undirected for community detection
        G_undirected = graph.to_undirected()

        # Run algorithm
        if algorithm == "louvain":
            if not LOUVAIN_AVAILABLE:
                raise ImportError("python-louvain not installed. Run: pip install python-louvain")

            communities = community_louvain.best_partition(
                G_undirected,
                resolution=resolution
            )
            modularity = community_louvain.modularity(communities, G_undirected)

        elif algorithm == "leiden":
            if not LEIDEN_AVAILABLE:
                raise ImportError("leidenalg not installed. Run: pip install leidenalg igraph")

            # Convert NetworkX to igraph
            G_ig = ig.Graph.from_networkx(G_undirected)
            partition = leidenalg.find_partition(
                G_ig,
                leidenalg.ModularityVertexPartition,
                resolution_parameter=resolution
            )

            # Map back to node IDs
            node_list = list(G_undirected.nodes())
            communities = {
                node_list[i]: partition.membership[i]
                for i in range(len(node_list))
            }
            modularity = partition.modularity

        elif algorithm == "label_propagation":
            communities_gen = nx.community.label_propagation_communities(G_undirected)
            communities = {}
            for i, comm in enumerate(communities_gen):
                for node in comm:
                    communities[node] = i

            # Calculate modularity
            community_list = [set() for _ in range(max(communities.values()) + 1)]
            for node, comm_id in communities.items():
                community_list[comm_id].add(node)
            modularity = nx.community.modularity(G_undirected, community_list)

        else:
            raise ValueError(f"Unknown algorithm: {algorithm}. Choose: louvain, leiden, label_propagation")

        # Filter small communities
        community_sizes = Counter(communities.values())
        filtered_communities = {
            node: comm_id
            for node, comm_id in communities.items()
            if community_sizes[comm_id] >= min_community_size
        }

        # Recalculate sizes
        final_sizes = Counter(filtered_communities.values())

        return CommunityResult(
            algorithm=algorithm,
            num_communities=len(final_sizes),
            modularity=modularity,
            communities=filtered_communities,
            community_sizes=dict(final_sizes),
            largest_community_size=max(final_sizes.values()) if final_sizes else 0
        )

    # ========================================================================
    # CENTRALITY METRICS
    # ========================================================================

    def calculate_centrality(
        self,
        layer: str = "paper",
        metric: str = "pagerank",
        top_k: int = 10,
        normalized: bool = True
    ) -> CentralityResult:
        """
        Calculate centrality metrics to find important nodes.

        Centrality metrics measure node importance:
        - degree: Number of connections (simple but effective)
        - betweenness: How often node appears on shortest paths (bridge nodes)
        - closeness: Average distance to all other nodes (central nodes)
        - pagerank: Importance based on connections' importance (Google's algorithm)
        - eigenvector: Importance of node's neighbors (quality over quantity)

        Args:
            layer: "paper" or "concept"
            metric: "degree", "betweenness", "closeness", "pagerank", "eigenvector"
            top_k: Return top K nodes
            normalized: Normalize scores to [0, 1]

        Returns:
            CentralityResult with top nodes and statistics
        """
        graph = self.kg.paper_graph if layer == "paper" else self.kg.concept_graph

        if graph.number_of_nodes() == 0:
            return CentralityResult(
                metric=metric,
                top_nodes=[],
                mean_score=0.0,
                median_score=0.0,
                max_score=0.0
            )

        # Calculate centrality
        if metric == "degree":
            if graph.is_directed():
                # For directed graphs, use out-degree (citations made)
                centrality = dict(graph.out_degree())
            else:
                centrality = dict(graph.degree())

            if normalized and centrality:
                max_val = max(centrality.values())
                if max_val > 0:
                    centrality = {k: v / max_val for k, v in centrality.items()}

        elif metric == "betweenness":
            centrality = nx.betweenness_centrality(graph, normalized=normalized)

        elif metric == "closeness":
            # Handle disconnected graphs
            if nx.is_strongly_connected(graph) if graph.is_directed() else nx.is_connected(graph):
                centrality = nx.closeness_centrality(graph, normalized=normalized)
            else:
                # Use local closeness for disconnected graphs
                centrality = {}
                for component in (nx.strongly_connected_components(graph) if graph.is_directed()
                                 else nx.connected_components(graph)):
                    if len(component) > 1:
                        subgraph = graph.subgraph(component)
                        local_closeness = nx.closeness_centrality(subgraph, normalized=normalized)
                        centrality.update(local_closeness)

        elif metric == "pagerank":
            centrality = nx.pagerank(graph, alpha=0.85)

        elif metric == "eigenvector":
            try:
                centrality = nx.eigenvector_centrality(graph, max_iter=1000)
            except nx.PowerIterationFailedConvergence:
                # Fall back to PageRank if eigenvector doesn't converge
                centrality = nx.pagerank(graph)

        else:
            raise ValueError(
                f"Unknown metric: {metric}. "
                f"Choose: degree, betweenness, closeness, pagerank, eigenvector"
            )

        # Sort and get top k
        sorted_nodes = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Calculate statistics
        scores = list(centrality.values())

        return CentralityResult(
            metric=metric,
            top_nodes=sorted_nodes,
            mean_score=float(np.mean(scores)) if scores else 0.0,
            median_score=float(np.median(scores)) if scores else 0.0,
            max_score=float(max(scores)) if scores else 0.0
        )

    # ========================================================================
    # GAP DETECTION
    # ========================================================================

    def detect_gaps(
        self,
        gap_type: str = "all",
        min_importance: float = 0.5,
        min_connections: int = 3,
        similarity_threshold: float = 0.7
    ) -> List[GapResult]:
        """
        Detect gaps in the research literature.

        Gap types:
        1. "isolated": Important concepts with few connections
        2. "disconnected_communities": Communities weakly connected to rest
        3. "missing_links": Similar concepts that aren't connected
        4. "all": All of the above

        Args:
            gap_type: Type of gap to detect
            min_importance: Minimum importance score (PageRank)
            min_connections: Maximum connections for "isolated" gaps
            similarity_threshold: Minimum similarity for "missing_links"

        Returns:
            List of GapResult objects
        """
        gaps = []

        # Type 1: Important but isolated concepts
        if gap_type in ["all", "isolated"]:
            gaps.extend(self._detect_isolated_important_concepts(
                min_importance=min_importance,
                max_connections=min_connections
            ))

        # Type 2: Disconnected communities
        if gap_type in ["all", "disconnected_communities"]:
            gaps.extend(self._detect_disconnected_communities())

        # Type 3: Missing links between similar concepts
        if gap_type in ["all", "missing_links"]:
            gaps.extend(self._detect_missing_links(
                similarity_threshold=similarity_threshold
            ))

        return gaps

    def _detect_isolated_important_concepts(
        self,
        min_importance: float,
        max_connections: int
    ) -> List[GapResult]:
        """Find important concepts with few connections."""
        gaps = []

        if self.kg.concept_graph.number_of_nodes() == 0:
            return gaps

        # Calculate importance (PageRank)
        pagerank = nx.pagerank(self.kg.concept_graph)
        degree = dict(self.kg.concept_graph.degree())

        for node_id, pr_score in pagerank.items():
            if pr_score >= min_importance and degree[node_id] <= max_connections:
                entity = self.kg.entities.get(node_id)

                # Get related entities
                related = list(self.kg.concept_graph.neighbors(node_id))[:5]
                related_texts = [
                    self.kg.entities[r].text
                    for r in related
                    if r in self.kg.entities
                ]

                gaps.append(GapResult(
                    gap_type="isolated_important_concept",
                    entity_id=node_id,
                    entity_text=entity.text if entity else node_id,
                    importance_score=pr_score,
                    connections=degree[node_id],
                    reason=(
                        f"High importance (PageRank={pr_score:.3f}) "
                        f"but only {degree[node_id]} connections. "
                        f"This concept may be underexplored."
                    ),
                    related_entities=related_texts,
                    evidence={
                        "pagerank": pr_score,
                        "degree": degree[node_id],
                        "entity_type": entity.entity_type if entity else "unknown"
                    }
                ))

        return gaps

    def _detect_disconnected_communities(self) -> List[GapResult]:
        """Find communities weakly connected to rest of network."""
        gaps = []

        if self.kg.concept_graph.number_of_nodes() < 10:
            return gaps

        # Detect communities
        try:
            comm_result = self.detect_communities(layer="concept", algorithm="louvain")
        except Exception:
            return gaps

        # Analyze each community
        for comm_id, size in comm_result.community_sizes.items():
            if size < 5:  # Skip small communities
                continue

            # Count internal vs external edges
            internal_edges = 0
            external_edges = 0
            community_nodes = [
                n for n, c in comm_result.communities.items() if c == comm_id
            ]

            for node in community_nodes:
                for neighbor in self.kg.concept_graph.neighbors(node):
                    if comm_result.communities.get(neighbor) == comm_id:
                        internal_edges += 1
                    else:
                        external_edges += 1

            # Flag if mostly isolated
            if internal_edges > 10 and external_edges < 3:
                # Get sample entities
                sample_entities = community_nodes[:5]
                sample_texts = [
                    self.kg.entities[e].text
                    for e in sample_entities
                    if e in self.kg.entities
                ]

                gaps.append(GapResult(
                    gap_type="disconnected_community",
                    entity_id=None,
                    entity_text=f"Community #{comm_id}",
                    importance_score=size / len(comm_result.communities),
                    connections=external_edges,
                    reason=(
                        f"Community of {size} concepts with {internal_edges} internal "
                        f"connections but only {external_edges} external connections. "
                        f"This research area may be isolated from the broader field."
                    ),
                    related_entities=sample_texts,
                    evidence={
                        "community_id": comm_id,
                        "size": size,
                        "internal_edges": internal_edges,
                        "external_edges": external_edges,
                        "isolation_ratio": internal_edges / (internal_edges + external_edges) if (internal_edges + external_edges) > 0 else 0
                    }
                ))

        return gaps

    def _detect_missing_links(self, similarity_threshold: float) -> List[GapResult]:
        """Find similar concepts that aren't connected."""
        gaps = []

        # Sample entities for performance (full analysis would be O(n²))
        entities_list = list(self.kg.entities.values())
        sample_size = min(100, len(entities_list))

        import random
        sampled = random.sample(entities_list, sample_size) if len(entities_list) > sample_size else entities_list

        for entity1 in sampled:
            similar = self.kg.find_similar_entities(entity1, limit=5)

            for entity2, similarity in similar:
                if similarity >= similarity_threshold:
                    # Check if connected
                    if not self.kg.concept_graph.has_edge(entity1.entity_id, entity2.entity_id):
                        gaps.append(GapResult(
                            gap_type="missing_link",
                            entity_id=entity1.entity_id,
                            entity_text=entity1.text,
                            importance_score=similarity,
                            connections=0,  # Not connected
                            reason=(
                                f"'{entity1.text}' and '{entity2.text}' are highly similar "
                                f"(similarity={similarity:.3f}) but not connected in the literature. "
                                f"Research linking these concepts may be missing."
                            ),
                            related_entities=[entity2.text],
                            evidence={
                                "entity1": entity1.text,
                                "entity2": entity2.text,
                                "similarity": similarity,
                                "entity1_type": entity1.entity_type,
                                "entity2_type": entity2.entity_type
                            }
                        ))

        return gaps

    # ========================================================================
    # ECHO CHAMBER DETECTION
    # ========================================================================

    def find_echo_chambers(
        self,
        min_cluster_size: int = 5,
        internal_ratio_threshold: float = 0.7,
        min_suspicion_score: float = 0.6
    ) -> List[EchoChamberResult]:
        """
        Detect citation rings and echo chambers.

        Echo chambers are groups of papers that cite each other disproportionately,
        potentially indicating citation manipulation or insular research communities.

        Detection patterns:
        1. Strongly connected components (citation cycles)
        2. High internal vs external citation ratio
        3. Isolated highly-cited clusters

        Args:
            min_cluster_size: Minimum papers in a suspicious cluster
            internal_ratio_threshold: Minimum internal citation ratio (0-1)
            min_suspicion_score: Minimum suspicion score to report

        Returns:
            List of suspicious clusters with evidence
        """
        echo_chambers = []

        if self.kg.paper_graph.number_of_nodes() < min_cluster_size:
            return echo_chambers

        # Find strongly connected components (citation cycles)
        strongly_connected = list(nx.strongly_connected_components(self.kg.paper_graph))

        for i, component in enumerate(strongly_connected):
            if len(component) < min_cluster_size:
                continue

            # Calculate internal vs external citations
            internal_citations = 0
            external_citations = 0

            for paper_id in component:
                if paper_id not in self.kg.papers:
                    continue

                paper = self.kg.papers[paper_id]
                for ref_id in paper.references:
                    if ref_id in component:
                        internal_citations += 1
                    else:
                        external_citations += 1

            total_citations = internal_citations + external_citations
            if total_citations == 0:
                continue

            internal_ratio = internal_citations / total_citations

            # Calculate suspicion score (0-1)
            # Factors: internal ratio, cluster size, isolation
            suspicion_score = (
                internal_ratio * 0.5 +  # Internal citation ratio
                min(len(component) / 20, 1) * 0.3 +  # Cluster size (capped at 20)
                (1 - min(external_citations / 10, 1)) * 0.2  # External citations (inverse)
            )

            if internal_ratio >= internal_ratio_threshold and suspicion_score >= min_suspicion_score:
                # Get paper titles
                papers = [
                    self.kg.papers[pid]
                    for pid in list(component)[:10]  # Sample
                    if pid in self.kg.papers
                ]

                echo_chambers.append(EchoChamberResult(
                    cluster_id=i,
                    size=len(component),
                    node_ids=list(component),
                    node_titles=[p.title for p in papers],
                    internal_citations=internal_citations,
                    external_citations=external_citations,
                    internal_ratio=internal_ratio,
                    suspicion_score=suspicion_score,
                    reason=(
                        f"Cluster of {len(component)} papers with {internal_ratio:.1%} "
                        f"internal citations. This may indicate a citation ring or "
                        f"insular research community. Suspicion score: {suspicion_score:.2f}"
                    )
                ))

        # Sort by suspicion score
        echo_chambers.sort(key=lambda x: x.suspicion_score, reverse=True)

        return echo_chambers

    # ========================================================================
    # PATH ANALYSIS
    # ========================================================================

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_paths: int = 5,
        max_length: int = 5
    ) -> Dict[str, Any]:
        """
        Find paths between two nodes (papers or concepts).

        Useful for understanding how ideas are connected through the literature.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_paths: Maximum number of paths to return
            max_length: Maximum path length to consider

        Returns:
            Dictionary with paths and analysis
        """
        # Determine which graph to use
        if source_id in self.kg.papers and target_id in self.kg.papers:
            graph = self.kg.paper_graph
            node_type = "paper"
        elif source_id in self.kg.entities and target_id in self.kg.entities:
            graph = self.kg.concept_graph.to_undirected()  # Use undirected for concepts
            node_type = "concept"
        else:
            return {
                "found": False,
                "reason": "Source and target must be both papers or both concepts"
            }

        # Check if nodes exist
        if source_id not in graph or target_id not in graph:
            return {
                "found": False,
                "reason": "Source or target node not found in graph"
            }

        # Find shortest path
        try:
            shortest_path = nx.shortest_path(graph, source_id, target_id)
            shortest_length = len(shortest_path) - 1
        except nx.NetworkXNoPath:
            return {
                "found": False,
                "reason": "No path exists between source and target",
                "source": source_id,
                "target": target_id
            }

        # Find multiple simple paths
        try:
            all_paths = list(nx.all_simple_paths(
                graph,
                source_id,
                target_id,
                cutoff=max_length
            ))
            all_paths = all_paths[:max_paths]  # Limit number
        except nx.NetworkXNoPath:
            all_paths = [shortest_path]

        # Get node details
        def get_node_text(node_id):
            if node_type == "paper":
                paper = self.kg.papers.get(node_id)
                return paper.title if paper else node_id
            else:
                entity = self.kg.entities.get(node_id)
                return entity.text if entity else node_id

        # Format paths
        formatted_paths = []
        for path in all_paths:
            formatted_paths.append({
                "length": len(path) - 1,
                "nodes": [get_node_text(n) for n in path],
                "node_ids": path
            })

        return {
            "found": True,
            "node_type": node_type,
            "shortest_path_length": shortest_length,
            "num_paths_found": len(formatted_paths),
            "paths": formatted_paths,
            "source_text": get_node_text(source_id),
            "target_text": get_node_text(target_id)
        }

    # ========================================================================
    # AUTHOR NETWORK ANALYSIS
    # ========================================================================

    def analyze_author_network(self, top_k: int = 20) -> Dict[str, Any]:
        """
        Analyze author collaboration network.

        Builds co-authorship network and finds:
        - Most collaborative authors
        - Research groups (communities)
        - Bridge authors connecting groups

        Args:
            top_k: Number of top authors to return

        Returns:
            Analysis results
        """
        # Build co-authorship network
        coauthor_graph = nx.Graph()

        for paper in self.kg.papers.values():
            authors = [a.name for a in paper.authors]

            # Add edges between all co-authors
            for i, author1 in enumerate(authors):
                for author2 in authors[i+1:]:
                    if coauthor_graph.has_edge(author1, author2):
                        # Increment weight (number of collaborations)
                        coauthor_graph[author1][author2]['weight'] += 1
                    else:
                        coauthor_graph.add_edge(author1, author2, weight=1)

        if coauthor_graph.number_of_nodes() == 0:
            return {"found": False, "reason": "No author data available"}

        # Calculate metrics
        degree = dict(coauthor_graph.degree())
        top_collaborative = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Detect research groups
        try:
            if LOUVAIN_AVAILABLE:
                communities = community_louvain.best_partition(coauthor_graph)
                num_groups = len(set(communities.values()))
            else:
                communities = {}
                num_groups = 0
        except Exception:
            communities = {}
            num_groups = 0

        # Find bridge authors (high betweenness)
        if coauthor_graph.number_of_nodes() > 2:
            betweenness = nx.betweenness_centrality(coauthor_graph)
            bridge_authors = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_k]
        else:
            bridge_authors = []

        return {
            "found": True,
            "total_authors": coauthor_graph.number_of_nodes(),
            "total_collaborations": coauthor_graph.number_of_edges(),
            "most_collaborative": top_collaborative,
            "research_groups": num_groups,
            "bridge_authors": bridge_authors,
            "average_collaborators": sum(degree.values()) / len(degree) if degree else 0
        }
