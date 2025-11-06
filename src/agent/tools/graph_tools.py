"""Graph analysis tools for the agent.

Wraps GraphAnalyzer methods as individual tools that the agent can use.
Each tool is atomic and focused on a single analysis task.
"""

from typing import Dict, Any, List, Optional
from ...analysis import GraphAnalyzer


class DetectCommunitiesTool:
    """
    Detect research communities (clusters) in the network.

    Communities are groups of papers or concepts that are more densely connected
    to each other than to the rest of the network. Useful for identifying
    research subfields, schools of thought, or topic clusters.
    """

    name = "detect_communities"
    description = """
    Detect communities (research clusters) in the network.

    Use this when you need to:
    - Identify research subfields or topic clusters
    - Find groups of closely related papers
    - Understand the structure of the research field
    - See how the literature is organized

    Parameters:
    - layer: "paper" (citation network) or "concept" (entity network)
    - algorithm: "louvain" (fast, default), "leiden" (more accurate), or "label_propagation" (simple)
    - resolution: Higher = more smaller communities (default: 1.0)
    - min_size: Filter out communities smaller than this (default: 2)

    Returns communities with modularity scores, sizes, and member assignments.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(
        self,
        layer: str = "paper",
        algorithm: str = "louvain",
        resolution: float = 1.0,
        min_size: int = 2
    ) -> Dict[str, Any]:
        """Execute community detection."""
        try:
            result = self.analyzer.detect_communities(
                layer=layer,
                algorithm=algorithm,
                resolution=resolution,
                min_community_size=min_size
            )

            return {
                "success": True,
                "algorithm": result.algorithm,
                "num_communities": result.num_communities,
                "modularity": round(result.modularity, 3),
                "largest_community": result.largest_community_size,
                "community_sizes": dict(sorted(
                    result.community_sizes.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]),  # Top 10 communities
                "total_nodes": len(result.communities),
                "interpretation": self._interpret_results(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, result) -> str:
        """Generate human-readable interpretation."""
        if result.num_communities == 0:
            return "No communities found in the network."

        quality = "high" if result.modularity > 0.5 else "moderate" if result.modularity > 0.3 else "low"

        return (
            f"Found {result.num_communities} research communities with {quality} modularity "
            f"({result.modularity:.3f}). The largest community contains {result.largest_community_size} "
            f"nodes. This suggests the field has "
            f"{'well-defined' if quality == 'high' else 'some'} sub-communities."
        )


class CalculateCentralityTool:
    """
    Calculate centrality metrics to find important/influential nodes.

    Centrality measures node importance in the network. Different metrics
    capture different aspects of importance:
    - degree: Number of connections (popularity)
    - pagerank: Importance based on neighbor importance (Google's algorithm)
    - betweenness: Bridge nodes connecting different parts
    - closeness: Central nodes close to all others
    - eigenvector: Quality of connections over quantity
    """

    name = "calculate_centrality"
    description = """
    Find the most important/influential papers or concepts using centrality metrics.

    Use this when you need to:
    - Identify the most influential papers in the field
    - Find key concepts that tie the literature together
    - Discover bridge papers connecting different research areas
    - Understand which work is most central to the field

    Parameters:
    - layer: "paper" (citation network) or "concept" (entity network)
    - metric: "pagerank" (recommended), "betweenness", "closeness", "degree", or "eigenvector"
    - top_k: Number of top nodes to return (default: 10)

    Each metric reveals different aspects of importance:
    - pagerank: Papers cited by other important papers
    - betweenness: Papers that bridge different research areas
    - closeness: Papers central to the field
    - degree: Most cited/connected papers
    - eigenvector: Papers with high-quality connections

    Returns top influential nodes with scores and interpretation.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(
        self,
        layer: str = "paper",
        metric: str = "pagerank",
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Execute centrality calculation."""
        try:
            result = self.analyzer.calculate_centrality(
                layer=layer,
                metric=metric,
                top_k=top_k
            )

            # Get node details
            top_nodes_with_details = []
            for node_id, score in result.top_nodes:
                if layer == "paper":
                    paper = self.analyzer.kg.papers.get(node_id)
                    if paper:
                        top_nodes_with_details.append({
                            "id": node_id,
                            "title": paper.title,
                            "year": paper.year,
                            "authors": [a.name for a in paper.authors][:3],  # First 3
                            "citations": paper.metadata.citation_count,
                            "score": round(score, 4)
                        })
                else:  # concept
                    entity = self.analyzer.kg.entities.get(node_id)
                    if entity:
                        top_nodes_with_details.append({
                            "id": node_id,
                            "text": entity.text,
                            "type": entity.entity_type,
                            "score": round(score, 4)
                        })

            return {
                "success": True,
                "metric": metric,
                "layer": layer,
                "top_nodes": top_nodes_with_details,
                "statistics": {
                    "mean": round(result.mean_score, 4),
                    "median": round(result.median_score, 4),
                    "max": round(result.max_score, 4)
                },
                "interpretation": self._interpret_results(result, layer, metric)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, result, layer, metric) -> str:
        """Generate human-readable interpretation."""
        metric_names = {
            "pagerank": "importance based on citation patterns",
            "betweenness": "bridging between research areas",
            "closeness": "centrality in the field",
            "degree": "number of connections",
            "eigenvector": "quality of connections"
        }

        if not result.top_nodes:
            return f"No nodes found in the {layer} network."

        top_score = result.top_nodes[0][1]
        avg_score = result.mean_score

        concentration = "highly concentrated" if top_score > avg_score * 10 else "moderately distributed"

        return (
            f"The {layer} network shows {concentration} {metric_names.get(metric, metric)}. "
            f"The top node has a score of {top_score:.4f}, which is "
            f"{top_score / avg_score:.1f}x the average ({avg_score:.4f})."
        )


class DetectGapsTool:
    """
    Detect gaps in the research literature.

    Finds underexplored areas, disconnected concepts, and missing connections
    that represent research opportunities.
    """

    name = "detect_gaps"
    description = """
    Find gaps in the research literature - underexplored areas and missing connections.

    Use this when you need to:
    - Identify research opportunities
    - Find important but underexplored concepts
    - Discover missing connections between related ideas
    - Spot isolated research areas

    Gap types:
    - "isolated": Important concepts with few connections (underexplored topics)
    - "disconnected_communities": Research areas isolated from the broader field
    - "missing_links": Similar concepts that aren't connected (potential research bridges)
    - "all": Detect all types of gaps (default)

    Parameters:
    - gap_type: Type of gap to detect (default: "all")
    - min_importance: Minimum importance score 0-1 (default: 0.5)
    - min_connections: Max connections for "isolated" gaps (default: 3)
    - similarity_threshold: Min similarity for "missing_links" (default: 0.7)

    Returns list of gaps with evidence, importance scores, and research opportunity explanations.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(
        self,
        gap_type: str = "all",
        min_importance: float = 0.5,
        min_connections: int = 3,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Execute gap detection."""
        try:
            gaps = self.analyzer.detect_gaps(
                gap_type=gap_type,
                min_importance=min_importance,
                min_connections=min_connections,
                similarity_threshold=similarity_threshold
            )

            # Format gaps for agent
            formatted_gaps = []
            for gap in gaps[:20]:  # Top 20 gaps
                formatted_gaps.append({
                    "type": gap.gap_type,
                    "entity": gap.entity_text,
                    "importance": round(gap.importance_score, 3),
                    "connections": gap.connections,
                    "reason": gap.reason,
                    "related": gap.related_entities[:5],  # Top 5 related
                    "evidence": gap.evidence
                })

            # Group by type
            by_type = {}
            for gap in formatted_gaps:
                gap_type = gap["type"]
                if gap_type not in by_type:
                    by_type[gap_type] = []
                by_type[gap_type].append(gap)

            return {
                "success": True,
                "num_gaps": len(formatted_gaps),
                "gaps": formatted_gaps,
                "by_type": {k: len(v) for k, v in by_type.items()},
                "interpretation": self._interpret_results(formatted_gaps, by_type)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, gaps, by_type) -> str:
        """Generate human-readable interpretation."""
        if not gaps:
            return "No significant gaps detected in the literature."

        total = len(gaps)
        types = ", ".join([f"{count} {gtype}" for gtype, count in by_type.items()])

        return (
            f"Found {total} potential gaps in the literature: {types}. "
            f"These represent research opportunities where important concepts are "
            f"underexplored, disconnected from the field, or missing connections to related work."
        )


class FindEchoChambersTool:
    """
    Detect citation rings and echo chambers.

    Finds groups of papers that cite each other disproportionately,
    potentially indicating citation manipulation or insular research communities.
    """

    name = "find_echo_chambers"
    description = """
    Detect citation rings and echo chambers in the literature.

    Use this when you need to:
    - Identify potential citation manipulation
    - Find insular research communities
    - Detect self-referential citation patterns
    - Assess the integrity of citation networks

    Echo chambers are groups of papers that cite each other heavily but have
    limited citations outside the group. This can indicate:
    - Citation rings (organized citation manipulation)
    - Insular research communities (limited external engagement)
    - Self-reinforcing research bubbles

    Parameters:
    - min_cluster_size: Minimum papers in a suspicious cluster (default: 5)
    - internal_ratio_threshold: Minimum internal citation ratio 0-1 (default: 0.7)
    - min_suspicion_score: Minimum suspicion score 0-1 to report (default: 0.6)

    Returns suspicious clusters with citation patterns, suspicion scores, and evidence.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(
        self,
        min_cluster_size: int = 5,
        internal_ratio_threshold: float = 0.7,
        min_suspicion_score: float = 0.6
    ) -> Dict[str, Any]:
        """Execute echo chamber detection."""
        try:
            chambers = self.analyzer.find_echo_chambers(
                min_cluster_size=min_cluster_size,
                internal_ratio_threshold=internal_ratio_threshold,
                min_suspicion_score=min_suspicion_score
            )

            # Format for agent
            formatted = []
            for chamber in chambers:
                formatted.append({
                    "cluster_id": chamber.cluster_id,
                    "size": chamber.size,
                    "sample_papers": chamber.node_titles[:5],  # First 5
                    "internal_citations": chamber.internal_citations,
                    "external_citations": chamber.external_citations,
                    "internal_ratio": round(chamber.internal_ratio, 3),
                    "suspicion_score": round(chamber.suspicion_score, 3),
                    "reason": chamber.reason
                })

            return {
                "success": True,
                "num_chambers": len(formatted),
                "chambers": formatted,
                "interpretation": self._interpret_results(formatted)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, chambers) -> str:
        """Generate human-readable interpretation."""
        if not chambers:
            return "No significant echo chambers or citation rings detected. The citation network appears healthy."

        high_suspicion = sum(1 for c in chambers if c["suspicion_score"] > 0.8)
        total = len(chambers)

        if high_suspicion > 0:
            severity = "concerning"
        elif total > 5:
            severity = "notable"
        else:
            severity = "minor"

        return (
            f"Detected {total} potential echo chambers with {severity} citation patterns. "
            f"{high_suspicion} clusters have high suspicion scores (>0.8), indicating possible "
            f"citation manipulation or highly insular research communities. "
            f"These clusters cite each other heavily but have limited external engagement."
        )


class AnalyzePathsTool:
    """
    Find and analyze paths between papers or concepts.

    Useful for understanding how ideas are connected through the literature.
    """

    name = "analyze_paths"
    description = """
    Find paths connecting two papers or concepts in the network.

    Use this when you need to:
    - Understand how two ideas are connected
    - Trace knowledge flow between papers
    - Find intermediate papers bridging two works
    - Discover the intellectual lineage between concepts

    Parameters:
    - source_id: ID of source paper or concept
    - target_id: ID of target paper or concept
    - max_paths: Maximum number of paths to find (default: 5)
    - max_length: Maximum path length to consider (default: 5)

    Returns paths with their lengths, intermediate nodes, and analysis of connections.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(
        self,
        source_id: str,
        target_id: str,
        max_paths: int = 5,
        max_length: int = 5
    ) -> Dict[str, Any]:
        """Execute path analysis."""
        try:
            result = self.analyzer.find_paths(
                source_id=source_id,
                target_id=target_id,
                max_paths=max_paths,
                max_length=max_length
            )

            if not result["found"]:
                return {
                    "success": True,
                    "found": False,
                    "reason": result["reason"],
                    "source_id": source_id,
                    "target_id": target_id
                }

            return {
                "success": True,
                "found": True,
                "source": result["source_text"],
                "target": result["target_text"],
                "node_type": result["node_type"],
                "shortest_path_length": result["shortest_path_length"],
                "num_paths": result["num_paths_found"],
                "paths": result["paths"],
                "interpretation": self._interpret_results(result)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, result) -> str:
        """Generate human-readable interpretation."""
        if not result["found"]:
            return f"No path exists between the specified {result['node_type']}s."

        shortest = result["shortest_path_length"]
        num_paths = result["num_paths_found"]

        if shortest == 1:
            return f"Directly connected! The {result['node_type']}s have a direct relationship."
        elif shortest <= 2:
            return f"Closely connected with {shortest} hop(s). Found {num_paths} path(s) connecting them."
        else:
            return (
                f"Connected through {shortest} intermediate {result['node_type']}s. "
                f"Found {num_paths} different path(s), suggesting multiple routes of knowledge transfer."
            )


class AnalyzeAuthorNetworkTool:
    """
    Analyze author collaboration patterns and co-authorship networks.
    """

    name = "analyze_author_network"
    description = """
    Analyze author collaboration patterns and identify research groups.

    Use this when you need to:
    - Find the most collaborative authors
    - Identify research groups and communities
    - Discover bridge authors connecting different groups
    - Understand collaboration patterns in the field

    Parameters:
    - top_k: Number of top authors to return (default: 20)

    Returns collaboration statistics, most collaborative authors, research groups,
    and bridge authors who connect different communities.
    """

    def __init__(self, analyzer: GraphAnalyzer):
        self.analyzer = analyzer

    def __call__(self, top_k: int = 20) -> Dict[str, Any]:
        """Execute author network analysis."""
        try:
            result = self.analyzer.analyze_author_network(top_k=top_k)

            if not result["found"]:
                return {
                    "success": True,
                    "found": False,
                    "reason": result["reason"]
                }

            return {
                "success": True,
                "found": True,
                "total_authors": result["total_authors"],
                "total_collaborations": result["total_collaborations"],
                "avg_collaborators": round(result["average_collaborators"], 2),
                "research_groups": result["research_groups"],
                "most_collaborative": result["most_collaborative"][:top_k],
                "bridge_authors": result.get("bridge_authors", [])[:top_k],
                "interpretation": self._interpret_results(result)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, result) -> str:
        """Generate human-readable interpretation."""
        if not result["found"]:
            return "No author collaboration data available."

        total = result["total_authors"]
        collabs = result["total_collaborations"]
        groups = result["research_groups"]
        avg = result["average_collaborators"]

        return (
            f"The field has {total} authors with {collabs} collaboration relationships, "
            f"organized into {groups} research groups. On average, each author collaborates "
            f"with {avg:.1f} other authors. This suggests a "
            f"{'highly collaborative' if avg > 5 else 'moderately collaborative' if avg > 2 else 'individualistic'} "
            f"research community."
        )
