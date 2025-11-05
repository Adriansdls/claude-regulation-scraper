"""LangExtract integration for ontology-based knowledge extraction."""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    print("Warning: langextract not installed. Install with: pip install langextract")

from ..models.paper import Paper
from ..models.ontology import Ontology, Entity, Relationship
from ..models.extraction import ExtractionResult, Extraction
from ..infrastructure.llm_client import get_llm_client


class LangExtractWrapper:
    """Wrapper for LangExtract with ontology support."""

    def __init__(self, ontology: Ontology):
        """Initialize wrapper.

        Args:
            ontology: Ontology defining entities and relationships to extract
        """
        if not LANGEXTRACT_AVAILABLE:
            raise ImportError("langextract not installed")

        self.ontology = ontology
        self.llm = get_llm_client()

    async def extract_entities(
        self, paper: Paper, text: Optional[str] = None
    ) -> ExtractionResult:
        """Extract entities from paper using LangExtract.

        Args:
            paper: Paper to extract from
            text: Text to extract from (if None, uses paper.full_text)

        Returns:
            ExtractionResult with entities
        """
        if text is None:
            text = paper.full_text

        if not text:
            return ExtractionResult(
                paper_id=paper.paper_id,
                ontology_name=self.ontology.name,
                extraction_model="none",
            )

        start_time = datetime.now()

        # Extract for each entity type
        all_entities = []

        for entity_type in self.ontology.entity_types:
            entities = await self._extract_entity_type(
                text=text,
                entity_type=entity_type,
                paper_id=paper.paper_id,
            )
            all_entities.extend(entities)

        # Create result
        extraction_time = (datetime.now() - start_time).total_seconds()

        result = ExtractionResult(
            paper_id=paper.paper_id,
            ontology_name=self.ontology.name,
            entities=all_entities,
            extracted_at=datetime.now(),
            extraction_model="gemini-2.5-flash",  # Default for LangExtract
            extraction_time_seconds=extraction_time,
        )

        result.compute_statistics()

        return result

    async def _extract_entity_type(
        self, text: str, entity_type: Any, paper_id: str
    ) -> List[Entity]:
        """Extract entities of a specific type.

        Args:
            text: Text to extract from
            entity_type: EntityType from ontology
            paper_id: Paper ID for provenance

        Returns:
            List of Entity objects
        """
        # Prepare examples for LangExtract
        examples = self._prepare_examples(entity_type)

        # Create extraction prompt
        prompt = f"""Extract all instances of {entity_type.name} from this text.

{entity_type.description}

Return JSON array of extractions:
[
  {{
    "text": "exact text from paper",
    "attributes": {{{", ".join(f'"{k}": "value"' for k in entity_type.attributes.keys())}}},
    "span_start": start_char_offset,
    "span_end": end_char_offset
  }}
]

Examples of {entity_type.name}:
{chr(10).join(f"- {ex}" for ex in entity_type.examples)}

Text:
{text[:8000]}"""  # Limit to 8000 chars

        try:
            # Use LLM to extract (fallback if LangExtract has issues)
            response = await self.llm.complete_json(prompt, max_tokens=4000)

            extractions = response if isinstance(response, list) else response.get("extractions", [])

            # Convert to Entity objects
            entities = []
            for ext in extractions:
                entity = Entity(
                    entity_id=str(uuid.uuid4()),
                    entity_type=entity_type.name,
                    text=ext.get("text", ""),
                    attributes=ext.get("attributes", {}),
                    source_paper_id=paper_id,
                    span_start=ext.get("span_start"),
                    span_end=ext.get("span_end"),
                    confidence=0.8,  # Default confidence for LLM extraction
                )
                entities.append(entity)

            return entities

        except Exception as e:
            print(f"Error extracting {entity_type.name}: {e}")
            return []

    async def extract_relationships(
        self, paper: Paper, entities: List[Entity], text: Optional[str] = None
    ) -> List[Relationship]:
        """Extract relationships between entities.

        Args:
            paper: Paper to extract from
            entities: Previously extracted entities
            text: Text to extract from (if None, uses paper.full_text)

        Returns:
            List of Relationship objects
        """
        if not entities:
            return []

        if text is None:
            text = paper.full_text

        if not text:
            return []

        # Group entities by type for easier lookup
        entities_by_type = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)

        # Extract for each relationship type
        all_relationships = []

        for rel_type in self.ontology.relationship_types:
            relationships = await self._extract_relationship_type(
                text=text,
                rel_type=rel_type,
                entities=entities,
                entities_by_type=entities_by_type,
                paper_id=paper.paper_id,
            )
            all_relationships.extend(relationships)

        return all_relationships

    async def _extract_relationship_type(
        self,
        text: str,
        rel_type: Any,
        entities: List[Entity],
        entities_by_type: Dict[str, List[Entity]],
        paper_id: str,
    ) -> List[Relationship]:
        """Extract relationships of a specific type.

        Args:
            text: Text to extract from
            rel_type: RelationType from ontology
            entities: All extracted entities
            entities_by_type: Entities grouped by type
            paper_id: Paper ID for provenance

        Returns:
            List of Relationship objects
        """
        # Get relevant entities for this relationship type
        source_entities = []
        for src_type in rel_type.source_types:
            source_entities.extend(entities_by_type.get(src_type, []))

        target_entities = []
        for tgt_type in rel_type.target_types:
            target_entities.extend(entities_by_type.get(tgt_type, []))

        if not source_entities or not target_entities:
            return []

        # Create extraction prompt
        source_list = "\n".join(f"- {e.text} (ID: {e.entity_id})" for e in source_entities[:20])
        target_list = "\n".join(f"- {e.text} (ID: {e.entity_id})" for e in target_entities[:20])

        prompt = f"""Identify {rel_type.name} relationships in this text.

Relationship: {rel_type.name}
Description: {rel_type.description}

Source entities ({rel_type.source_types}):
{source_list}

Target entities ({rel_type.target_types}):
{target_list}

Return JSON array of relationships found:
[
  {{
    "source_entity_id": "id from source list",
    "target_entity_id": "id from target list",
    "evidence": "sentence or phrase showing relationship",
    "attributes": {{}}
  }}
]

Text:
{text[:8000]}"""

        try:
            response = await self.llm.complete_json(prompt, max_tokens=3000)

            rel_data = response if isinstance(response, list) else response.get("relationships", [])

            # Convert to Relationship objects
            relationships = []
            for rel in rel_data:
                relationship = Relationship(
                    relationship_id=str(uuid.uuid4()),
                    relationship_type=rel_type.name,
                    source_entity_id=rel.get("source_entity_id", ""),
                    target_entity_id=rel.get("target_entity_id", ""),
                    attributes=rel.get("attributes", {}),
                    source_paper_id=paper_id,
                    confidence=0.75,  # Default confidence
                    evidence=rel.get("evidence", ""),
                )
                relationships.append(relationship)

            return relationships

        except Exception as e:
            print(f"Error extracting {rel_type.name} relationships: {e}")
            return []

    def _prepare_examples(self, entity_type: Any) -> List[Dict[str, Any]]:
        """Prepare examples for LangExtract.

        Args:
            entity_type: EntityType from ontology

        Returns:
            List of example dictionaries
        """
        examples = []

        for example_text in entity_type.examples[:5]:  # Limit to 5 examples
            examples.append(
                {
                    "extraction_class": entity_type.name,
                    "extraction_text": example_text,
                    "attributes": {},  # Would need to be defined in ontology
                }
            )

        return examples

    async def extract_from_sections(
        self, paper: Paper, sections: Dict[str, str]
    ) -> ExtractionResult:
        """Extract entities from specific sections.

        More accurate than extracting from full text at once.

        Args:
            paper: Paper to extract from
            sections: Dict of section_name -> section_text

        Returns:
            ExtractionResult with entities from all sections
        """
        all_entities = []
        all_relationships = []

        # Extract entities from each section
        for section_name, section_text in sections.items():
            if not section_text or len(section_text) < 50:
                continue

            # Extract entities
            result = await self.extract_entities(paper, text=section_text)

            # Mark section in entities
            for entity in result.entities:
                entity.source_section = section_name

            all_entities.extend(result.entities)

        # Extract relationships using all entities
        relationships = await self.extract_relationships(paper, all_entities)
        all_relationships.extend(relationships)

        # Create combined result
        final_result = ExtractionResult(
            paper_id=paper.paper_id,
            ontology_name=self.ontology.name,
            entities=all_entities,
            relationships=all_relationships,
            extracted_at=datetime.now(),
            extraction_model="gemini-2.5-flash-sections",
        )

        final_result.compute_statistics()

        return final_result
