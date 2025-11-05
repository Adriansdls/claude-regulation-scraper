"""Ontology models for knowledge extraction."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EntityType(BaseModel):
    """Definition of an entity type in the ontology."""

    name: str
    description: str
    attributes: Dict[str, str] = Field(default_factory=dict)  # {attr_name: type}
    examples: List[str] = Field(default_factory=list)


class RelationType(BaseModel):
    """Definition of a relationship type in the ontology."""

    name: str
    description: str
    source_types: List[str]  # Allowed source entity types
    target_types: List[str]  # Allowed target entity types
    attributes: Dict[str, str] = Field(default_factory=dict)
    directional: bool = True  # Whether relationship has direction
    examples: List[str] = Field(default_factory=list)


class Ontology(BaseModel):
    """Ontology defining entities and relationships to extract."""

    name: str
    description: str
    domain: str  # e.g., "machine_learning", "biology", "general"
    version: str = "1.0.0"

    entity_types: List[EntityType] = Field(default_factory=list)
    relationship_types: List[RelationType] = Field(default_factory=list)

    # Optional: Few-shot examples for LangExtract
    extraction_examples: List[Dict[str, Any]] = Field(default_factory=list)

    def get_entity_type(self, name: str) -> Optional[EntityType]:
        """Get entity type by name."""
        for entity_type in self.entity_types:
            if entity_type.name == name:
                return entity_type
        return None

    def get_relationship_type(self, name: str) -> Optional[RelationType]:
        """Get relationship type by name."""
        for rel_type in self.relationship_types:
            if rel_type.name == name:
                return rel_type
        return None

    def validate_relationship(self, rel_name: str, source_type: str, target_type: str) -> bool:
        """Check if a relationship is valid for given entity types."""
        rel_type = self.get_relationship_type(rel_name)
        if not rel_type:
            return False

        source_valid = source_type in rel_type.source_types
        target_valid = target_type in rel_type.target_types

        return source_valid and target_valid

    def to_langextract_format(self) -> Dict[str, Any]:
        """Convert ontology to LangExtract format."""
        # LangExtract uses examples rather than explicit schemas
        return {
            "description": self.description,
            "entity_types": [
                {"class": et.name, "description": et.description, "examples": et.examples}
                for et in self.entity_types
            ],
            "relationship_types": [
                {
                    "type": rt.name,
                    "description": rt.description,
                    "source_types": rt.source_types,
                    "target_types": rt.target_types,
                }
                for rt in self.relationship_types
            ],
            "examples": self.extraction_examples,
        }


class Entity(BaseModel):
    """An extracted entity instance."""

    entity_id: str  # Unique ID for this entity
    entity_type: str  # Type from ontology
    text: str  # Text mention in source
    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Provenance
    source_paper_id: str
    source_section: Optional[str] = None  # Which section (intro, methods, etc.)
    span_start: Optional[int] = None  # Character offset in text
    span_end: Optional[int] = None

    # Confidence
    confidence: float = 1.0  # 0-1
    evidence: Optional[str] = None  # Supporting quote from text

    def __hash__(self):
        return hash(f"{self.entity_id}_{self.source_paper_id}")

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return (
            self.entity_id == other.entity_id and self.source_paper_id == other.source_paper_id
        )


class Relationship(BaseModel):
    """An extracted relationship between entities."""

    relationship_id: str
    relationship_type: str  # Type from ontology

    source_entity_id: str
    target_entity_id: str

    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Provenance
    source_paper_id: str
    source_section: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None

    # Confidence
    confidence: float = 1.0
    evidence: Optional[str] = None

    def __hash__(self):
        return hash(f"{self.relationship_id}_{self.source_paper_id}")

    def __eq__(self, other):
        if not isinstance(other, Relationship):
            return False
        return (
            self.relationship_id == other.relationship_id
            and self.source_paper_id == other.source_paper_id
        )
