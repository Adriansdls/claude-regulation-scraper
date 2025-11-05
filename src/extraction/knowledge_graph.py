"""Knowledge graph construction and management."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import networkx as nx

from ..models.paper import Paper
from ..models.ontology import Entity, Relationship, Ontology
from ..models.extraction import ExtractionResult


class KnowledgeGraph:
    """Multi-layer knowledge graph combining papers, entities, and relationships."""

    def __init__(self, ontology: Optional[Ontology] = None):
        """Initialize knowledge graph.

        Args:
            ontology: Ontology used for extraction (optional)
        """
        self.ontology = ontology

        # Layer 1: Paper citation network
        self.paper_graph = nx.DiGraph()

        # Layer 2: Concept/entity network
        self.concept_graph = nx.MultiDiGraph()

        # Cross-layer: paper -> concepts mapping
        self.paper_to_concepts: Dict[str, List[str]] = defaultdict(list)

        # Store extracted data
        self.entities: Dict[str, Entity] = {}  # entity_id -> Entity
        self.relationships: Dict[str, Relationship] = {}  # relationship_id -> Relationship
        self.papers: Dict[str, Paper] = {}  # paper_id -> Paper

    def add_paper(self, paper: Paper):
        """Add a paper to the graph.

        Args:
            paper: Paper to add
        """
        self.papers[paper.paper_id] = paper

        # Add to paper graph
        self.paper_graph.add_node(
            paper.paper_id,
            title=paper.title,
            year=paper.year,
            authors=[a.name for a in paper.authors],
            citation_count=paper.metadata.citation_count,
            venue=paper.metadata.venue,
        )

        # Add citation edges
        for ref_id in paper.references:
            if ref_id:  # Only if ref_id is not empty
                self.paper_graph.add_edge(paper.paper_id, ref_id, edge_type="cites")

        for cited_id in paper.cited_by:
            if cited_id:
                self.paper_graph.add_edge(cited_id, paper.paper_id, edge_type="cites")

    def add_extraction_result(self, result: ExtractionResult):
        """Add extraction results to the graph.

        Args:
            result: ExtractionResult with entities and relationships
        """
        # Add entities
        for entity in result.entities:
            self.add_entity(entity)

        # Add relationships
        for relationship in result.relationships:
            self.add_relationship(relationship)

    def add_entity(self, entity: Entity):
        """Add an entity to the concept graph.

        Args:
            entity: Entity to add
        """
        self.entities[entity.entity_id] = entity

        # Add to concept graph
        self.concept_graph.add_node(
            entity.entity_id,
            type=entity.entity_type,
            text=entity.text,
            attributes=entity.attributes,
            source_paper=entity.source_paper_id,
            source_section=entity.source_section,
            confidence=entity.confidence,
        )

        # Link paper to concept
        self.paper_to_concepts[entity.source_paper_id].append(entity.entity_id)

    def add_relationship(self, relationship: Relationship):
        """Add a relationship to the concept graph.

        Args:
            relationship: Relationship to add
        """
        self.relationships[relationship.relationship_id] = relationship

        # Add edge to concept graph
        if (
            relationship.source_entity_id in self.entities
            and relationship.target_entity_id in self.entities
        ):
            self.concept_graph.add_edge(
                relationship.source_entity_id,
                relationship.target_entity_id,
                key=relationship.relationship_id,
                type=relationship.relationship_type,
                attributes=relationship.attributes,
                source_paper=relationship.source_paper_id,
                confidence=relationship.confidence,
                evidence=relationship.evidence,
            )

    def get_paper_concepts(self, paper_id: str) -> List[Entity]:
        """Get all concepts/entities mentioned in a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of Entity objects
        """
        concept_ids = self.paper_to_concepts.get(paper_id, [])
        return [self.entities[cid] for cid in concept_ids if cid in self.entities]

    def get_concept_papers(self, entity_id: str) -> List[Paper]:
        """Get all papers that mention a concept.

        Args:
            entity_id: Entity ID

        Returns:
            List of Paper objects
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return []

        # Find all papers that mention this concept
        # (In a full implementation, would need entity linking/merging)
        papers = []
        if entity.source_paper_id in self.papers:
            papers.append(self.papers[entity.source_paper_id])

        return papers

    def get_entity_relationships(
        self, entity_id: str, direction: str = "both"
    ) -> List[Relationship]:
        """Get relationships involving an entity.

        Args:
            entity_id: Entity ID
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of Relationship objects
        """
        relationships = []

        if direction in ["outgoing", "both"]:
            for rel in self.relationships.values():
                if rel.source_entity_id == entity_id:
                    relationships.append(rel)

        if direction in ["incoming", "both"]:
            for rel in self.relationships.values():
                if rel.target_entity_id == entity_id:
                    relationships.append(rel)

        return relationships

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge graph.

        Returns:
            Statistics dictionary
        """
        # Paper statistics
        paper_stats = {
            "total_papers": len(self.papers),
            "papers_with_citations": sum(1 for p in self.paper_graph.nodes if self.paper_graph.degree(p) > 0),
            "total_citations": self.paper_graph.number_of_edges(),
        }

        # Entity statistics
        entity_by_type = defaultdict(int)
        for entity in self.entities.values():
            entity_by_type[entity.entity_type] += 1

        entity_stats = {
            "total_entities": len(self.entities),
            "by_type": dict(entity_by_type),
            "avg_confidence": (
                sum(e.confidence for e in self.entities.values()) / len(self.entities)
                if self.entities
                else 0
            ),
        }

        # Relationship statistics
        rel_by_type = defaultdict(int)
        for rel in self.relationships.values():
            rel_by_type[rel.relationship_type] += 1

        rel_stats = {
            "total_relationships": len(self.relationships),
            "by_type": dict(rel_by_type),
            "avg_confidence": (
                sum(r.confidence for r in self.relationships.values()) / len(self.relationships)
                if self.relationships
                else 0
            ),
        }

        # Network statistics
        network_stats = {
            "concept_graph_nodes": self.concept_graph.number_of_nodes(),
            "concept_graph_edges": self.concept_graph.number_of_edges(),
            "paper_graph_nodes": self.paper_graph.number_of_nodes(),
            "paper_graph_edges": self.paper_graph.number_of_edges(),
        }

        # Try to compute connectivity (may be slow for large graphs)
        if self.concept_graph.number_of_nodes() > 0 and self.concept_graph.number_of_nodes() < 10000:
            try:
                network_stats["concept_graph_components"] = nx.number_weakly_connected_components(
                    self.concept_graph
                )
            except Exception:
                pass

        return {
            "papers": paper_stats,
            "entities": entity_stats,
            "relationships": rel_stats,
            "network": network_stats,
        }

    def save(self, output_path: str):
        """Save knowledge graph to disk.

        Args:
            output_path: Path to save to (JSON format)
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "ontology": self.ontology.dict() if self.ontology else None,
            "papers": {pid: p.dict() for pid, p in self.papers.items()},
            "entities": {eid: e.dict() for eid, e in self.entities.items()},
            "relationships": {rid: r.dict() for rid, r in self.relationships.items()},
            "paper_to_concepts": {k: list(v) for k, v in self.paper_to_concepts.items()},
            "statistics": self.get_statistics(),
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load(cls, input_path: str) -> "KnowledgeGraph":
        """Load knowledge graph from disk.

        Args:
            input_path: Path to load from

        Returns:
            KnowledgeGraph instance
        """
        with open(input_path, "r") as f:
            data = json.load(f)

        # Reconstruct ontology
        ontology = None
        if data.get("ontology"):
            ontology = Ontology(**data["ontology"])

        kg = cls(ontology=ontology)

        # Reconstruct papers
        for paper_data in data.get("papers", {}).values():
            paper = Paper(**paper_data)
            kg.add_paper(paper)

        # Reconstruct entities
        for entity_data in data.get("entities", {}).values():
            entity = Entity(**entity_data)
            kg.add_entity(entity)

        # Reconstruct relationships
        for rel_data in data.get("relationships", {}).values():
            rel = Relationship(**rel_data)
            kg.add_relationship(rel)

        return kg

    def export_for_gephi(self, output_dir: str):
        """Export graph in Gephi-compatible format.

        Args:
            output_dir: Directory to save files to
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export concept graph
        nx.write_gexf(self.concept_graph, output_path / "concept_graph.gexf")

        # Export paper graph
        nx.write_gexf(self.paper_graph, output_path / "paper_graph.gexf")

        print(f"Exported graphs to {output_dir}")
        print(f"- concept_graph.gexf ({self.concept_graph.number_of_nodes()} nodes)")
        print(f"- paper_graph.gexf ({self.paper_graph.number_of_nodes()} nodes)")

    def get_subgraph_around_entity(
        self, entity_id: str, radius: int = 1
    ) -> nx.MultiDiGraph:
        """Get subgraph around an entity (ego graph).

        Args:
            entity_id: Entity ID
            radius: How many hops to include

        Returns:
            Subgraph as NetworkX MultiDiGraph
        """
        if entity_id not in self.concept_graph:
            return nx.MultiDiGraph()

        return nx.ego_graph(self.concept_graph, entity_id, radius=radius)

    def find_similar_entities(self, entity: Entity, limit: int = 10) -> List[Tuple[Entity, float]]:
        """Find entities similar to a given entity.

        Uses simple text similarity for now.

        Args:
            entity: Entity to find similar to
            limit: Maximum number of results

        Returns:
            List of (Entity, similarity_score) tuples
        """
        similar = []

        # Get entities of same type
        candidates = [e for e in self.entities.values() if e.entity_type == entity.entity_type and e.entity_id != entity.entity_id]

        # Simple text similarity (could be improved with embeddings)
        for candidate in candidates:
            # Jaccard similarity on words
            words1 = set(entity.text.lower().split())
            words2 = set(candidate.text.lower().split())

            if not words1 or not words2:
                continue

            similarity = len(words1 & words2) / len(words1 | words2)

            if similarity > 0.3:  # Threshold
                similar.append((candidate, similarity))

        # Sort by similarity
        similar.sort(key=lambda x: x[1], reverse=True)

        return similar[:limit]

    def merge_similar_entities(self, similarity_threshold: float = 0.8):
        """Merge entities that are very similar (entity linking).

        Args:
            similarity_threshold: Threshold for merging (0-1)
        """
        # Group entities by type
        by_type = defaultdict(list)
        for entity in self.entities.values():
            by_type[entity.entity_type].append(entity)

        merged_count = 0

        # For each type, find and merge similar entities
        for entity_type, entities in by_type.items():
            # Build similarity matrix (simplified version)
            to_merge = []

            for i, e1 in enumerate(entities):
                for e2 in entities[i + 1 :]:
                    words1 = set(e1.text.lower().split())
                    words2 = set(e2.text.lower().split())

                    if not words1 or not words2:
                        continue

                    similarity = len(words1 & words2) / len(words1 | words2)

                    if similarity >= similarity_threshold:
                        to_merge.append((e1.entity_id, e2.entity_id))

            # Merge entities (keep first, redirect second)
            # This is a simplified version - full implementation would update all relationships
            for id1, id2 in to_merge:
                if id2 in self.entities:
                    del self.entities[id2]
                    merged_count += 1

        print(f"Merged {merged_count} similar entities")
