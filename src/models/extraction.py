"""Models for extraction results."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .ontology import Entity, Relationship


class ExtractionResult(BaseModel):
    """Result of extracting entities/relationships from a paper."""

    paper_id: str
    ontology_name: str

    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)

    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    extraction_model: str  # Which LLM was used
    extraction_time_seconds: float = 0.0

    # Statistics
    entity_count_by_type: Dict[str, int] = Field(default_factory=dict)
    relationship_count_by_type: Dict[str, int] = Field(default_factory=dict)

    # Quality metrics
    avg_entity_confidence: float = 0.0
    avg_relationship_confidence: float = 0.0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def compute_statistics(self):
        """Compute statistics about the extraction."""
        # Count by type
        self.entity_count_by_type = {}
        for entity in self.entities:
            self.entity_count_by_type[entity.entity_type] = (
                self.entity_count_by_type.get(entity.entity_type, 0) + 1
            )

        self.relationship_count_by_type = {}
        for rel in self.relationships:
            self.relationship_count_by_type[rel.relationship_type] = (
                self.relationship_count_by_type.get(rel.relationship_type, 0) + 1
            )

        # Average confidence
        if self.entities:
            self.avg_entity_confidence = sum(e.confidence for e in self.entities) / len(
                self.entities
            )
        if self.relationships:
            self.avg_relationship_confidence = sum(r.confidence for r in self.relationships) / len(
                self.relationships
            )


class Extraction(BaseModel):
    """Wrapper for a single extraction (used with LangExtract)."""

    extraction_class: str  # Entity type
    extraction_text: str  # The extracted text
    attributes: Dict[str, Any] = Field(default_factory=dict)
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    confidence: float = 1.0
