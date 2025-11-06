"""Visualization tools for terminal output.

Provides beautiful visualizations using Rich library for the terminal interface.
"""

from typing import Dict, Any
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.console import Console


class ShowGraphStatsTool:
    """
    Display comprehensive statistics about the knowledge graph.

    Shows paper counts, entity counts, relationship counts, network statistics,
    and quality metrics in a beautiful formatted table.
    """

    name = "show_graph_stats"
    description = """
    Display comprehensive statistics about the knowledge graph.

    Use this when you need to:
    - Get an overview of the graph size and structure
    - Check data quality metrics
    - Understand the scope of the available data
    - Present summary statistics to the user

    Returns formatted statistics including:
    - Total papers, entities, relationships
    - Entity and relationship type distributions
    - Network sizes and connectivity
    - Quality metrics (average confidence, etc.)

    Output is formatted beautifully for terminal display.
    """

    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph
        self.console = Console()

    def __call__(self) -> Dict[str, Any]:
        """Show graph statistics."""
        try:
            stats = self.kg.get_statistics()

            # Format for terminal
            display_text = self._format_stats(stats)

            return {
                "success": True,
                "statistics": stats,
                "display": display_text,
                "interpretation": self._interpret_stats(stats)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _format_stats(self, stats: Dict) -> str:
        """Format statistics as beautiful text."""
        lines = []
        lines.append("=" * 60)
        lines.append("KNOWLEDGE GRAPH STATISTICS")
        lines.append("=" * 60)

        # Papers
        papers = stats.get("papers", {})
        lines.append(f"\n📚 PAPERS:")
        lines.append(f"  Total: {papers.get('total_papers', 0)}")
        lines.append(f"  With citations: {papers.get('papers_with_citations', 0)}")
        lines.append(f"  Total citations: {papers.get('total_citations', 0)}")

        # Entities
        entities = stats.get("entities", {})
        lines.append(f"\n🏷️  ENTITIES:")
        lines.append(f"  Total: {entities.get('total_entities', 0)}")
        lines.append(f"  Avg confidence: {entities.get('avg_confidence', 0):.2f}")
        by_type = entities.get("by_type", {})
        for etype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"    - {etype}: {count}")

        # Relationships
        relationships = stats.get("relationships", {})
        lines.append(f"\n🔗 RELATIONSHIPS:")
        lines.append(f"  Total: {relationships.get('total_relationships', 0)}")
        lines.append(f"  Avg confidence: {relationships.get('avg_confidence', 0):.2f}")
        by_type = relationships.get("by_type", {})
        for rtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"    - {rtype}: {count}")

        # Network
        network = stats.get("network", {})
        lines.append(f"\n🕸️  NETWORK:")
        lines.append(f"  Paper graph: {network.get('paper_graph_nodes', 0)} nodes, {network.get('paper_graph_edges', 0)} edges")
        lines.append(f"  Concept graph: {network.get('concept_graph_nodes', 0)} nodes, {network.get('concept_graph_edges', 0)} edges")
        if "concept_graph_components" in network:
            lines.append(f"  Components: {network['concept_graph_components']}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)

    def _interpret_stats(self, stats: Dict) -> str:
        """Generate human-readable interpretation."""
        papers = stats.get("papers", {}).get("total_papers", 0)
        entities = stats.get("entities", {}).get("total_entities", 0)
        relationships = stats.get("relationships", {}).get("total_relationships", 0)

        if papers == 0:
            return "Empty knowledge graph."

        entity_per_paper = entities / papers if papers > 0 else 0
        rel_per_paper = relationships / papers if papers > 0 else 0

        quality = "high" if entity_per_paper > 10 and rel_per_paper > 5 else "moderate" if entity_per_paper > 5 else "basic"

        return (
            f"Knowledge graph contains {papers} papers with {entities} extracted entities "
            f"and {relationships} relationships. Extraction quality is {quality} "
            f"({entity_per_paper:.1f} entities and {rel_per_paper:.1f} relationships per paper on average)."
        )


class VisualizeNetworkTool:
    """
    Create terminal-friendly visualizations of the network.

    Generates ASCII art or tree-based visualizations that look great in the terminal.
    """

    name = "visualize_network"
    description = """
    Create visual representations of the network for terminal display.

    Use this when you need to:
    - Show network structure visually
    - Display community organization
    - Illustrate citation relationships
    - Help user understand graph topology

    Parameters:
    - view_type: "communities" (show research clusters), "tree" (hierarchical view),
                 "top_papers" (most influential papers), or "connections" (specific relationships)
    - max_nodes: Maximum nodes to display (default: 20)
    - focal_node: Optional node ID to focus visualization around

    Returns visualization formatted for terminal using Rich library (trees, panels, etc).
    """

    def __init__(self, knowledge_graph, analyzer):
        self.kg = knowledge_graph
        self.analyzer = analyzer

    def __call__(
        self,
        view_type: str = "communities",
        max_nodes: int = 20,
        focal_node: str = None
    ) -> Dict[str, Any]:
        """Create network visualization."""
        try:
            if view_type == "communities":
                display = self._visualize_communities(max_nodes)
            elif view_type == "tree":
                display = self._visualize_tree(max_nodes, focal_node)
            elif view_type == "top_papers":
                display = self._visualize_top_papers(max_nodes)
            elif view_type == "connections":
                display = self._visualize_connections(max_nodes, focal_node)
            else:
                return {
                    "success": False,
                    "error": f"Unknown view_type: {view_type}. Choose: communities, tree, top_papers, connections"
                }

            return {
                "success": True,
                "view_type": view_type,
                "display": display,
                "interpretation": f"Showing {view_type} view of the network"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _visualize_communities(self, max_nodes: int) -> str:
        """Visualize research communities."""
        result = self.analyzer.detect_communities(layer="paper", algorithm="louvain")

        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("RESEARCH COMMUNITIES")
        lines.append("=" * 60)

        # Show top communities
        sorted_communities = sorted(
            result.community_sizes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        for comm_id, size in sorted_communities:
            lines.append(f"\n📁 Community {comm_id} ({size} papers)")

            # Get sample papers from this community
            papers_in_comm = [
                pid for pid, cid in result.communities.items()
                if cid == comm_id
            ][:3]  # Show 3 samples

            for pid in papers_in_comm:
                if pid in self.kg.papers:
                    paper = self.kg.papers[pid]
                    lines.append(f"  • {paper.title[:60]}...")

        return "\n".join(lines)

    def _visualize_tree(self, max_nodes: int, focal_node: str) -> str:
        """Visualize as hierarchical tree."""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("CITATION TREE")
        lines.append("=" * 60)

        if not focal_node and self.kg.papers:
            # Use most cited paper as root
            papers = list(self.kg.papers.values())
            focal_node = max(papers, key=lambda p: p.metadata.citation_count).paper_id

        if focal_node and focal_node in self.kg.papers:
            root_paper = self.kg.papers[focal_node]
            lines.append(f"\n🌳 Root: {root_paper.title}")

            # Show papers it cites
            if root_paper.references:
                lines.append("\n  📖 References:")
                for ref_id in root_paper.references[:5]:
                    if ref_id in self.kg.papers:
                        ref = self.kg.papers[ref_id]
                        lines.append(f"    ↳ {ref.title[:50]}...")

            # Show papers citing it
            if root_paper.cited_by:
                lines.append("\n  📚 Cited by:")
                for cite_id in root_paper.cited_by[:5]:
                    if cite_id in self.kg.papers:
                        cite = self.kg.papers[cite_id]
                        lines.append(f"    ↲ {cite.title[:50]}...")

        return "\n".join(lines)

    def _visualize_top_papers(self, max_nodes: int) -> str:
        """Visualize top influential papers."""
        result = self.analyzer.calculate_centrality(
            layer="paper",
            metric="pagerank",
            top_k=max_nodes
        )

        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("TOP INFLUENTIAL PAPERS (PageRank)")
        lines.append("=" * 60)

        for i, (paper_id, score) in enumerate(result.top_nodes, 1):
            if paper_id in self.kg.papers:
                paper = self.kg.papers[paper_id]
                lines.append(f"\n{i}. {paper.title}")
                lines.append(f"   Score: {score:.4f} | Year: {paper.year} | Citations: {paper.metadata.citation_count}")
                if paper.authors:
                    authors = ", ".join([a.name for a in paper.authors[:3]])
                    lines.append(f"   Authors: {authors}")

        return "\n".join(lines)

    def _visualize_connections(self, max_nodes: int, focal_node: str) -> str:
        """Visualize connections around a focal node."""
        if not focal_node:
            return "Error: focal_node required for connections view"

        lines = []
        lines.append("\n" + "=" * 60)
        lines.append(f"CONNECTIONS FOR NODE: {focal_node}")
        lines.append("=" * 60)

        if focal_node in self.kg.paper_graph:
            # Get neighbors
            out_neighbors = list(self.kg.paper_graph.successors(focal_node))[:max_nodes]
            in_neighbors = list(self.kg.paper_graph.predecessors(focal_node))[:max_nodes]

            if focal_node in self.kg.papers:
                paper = self.kg.papers[focal_node]
                lines.append(f"\n📄 {paper.title}")

            if out_neighbors:
                lines.append(f"\n→ References ({len(out_neighbors)}):")
                for neighbor in out_neighbors[:5]:
                    if neighbor in self.kg.papers:
                        p = self.kg.papers[neighbor]
                        lines.append(f"  • {p.title[:50]}...")

            if in_neighbors:
                lines.append(f"\n← Cited by ({len(in_neighbors)}):")
                for neighbor in in_neighbors[:5]:
                    if neighbor in self.kg.papers:
                        p = self.kg.papers[neighbor]
                        lines.append(f"  • {p.title[:50]}...")

        return "\n".join(lines)
