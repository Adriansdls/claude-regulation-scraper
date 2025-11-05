"""Extraction orchestrator - manages complete extraction pipeline."""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.paper import Paper
from ..models.ontology import Ontology
from ..models.extraction import ExtractionResult
from .pdf_downloader import PDFDownloader
from .text_extractor import TextExtractor
from .langextract_wrapper import LangExtractWrapper
from .knowledge_graph import KnowledgeGraph


class ExtractionOrchestrator:
    """Orchestrates the complete extraction pipeline."""

    def __init__(self, ontology: Ontology):
        """Initialize orchestrator.

        Args:
            ontology: Ontology for extraction
        """
        self.ontology = ontology
        self.pdf_downloader = PDFDownloader()
        self.text_extractor = TextExtractor()
        self.extractor = LangExtractWrapper(ontology)
        self.knowledge_graph = KnowledgeGraph(ontology)

    async def extract_from_papers(
        self,
        papers: List[Paper],
        download_pdfs: bool = True,
        max_papers: Optional[int] = None,
    ) -> KnowledgeGraph:
        """Run complete extraction pipeline on papers.

        Pipeline:
        1. Download PDFs (if requested)
        2. Extract text from PDFs
        3. Parse text into sections
        4. Extract entities using LangExtract
        5. Extract relationships
        6. Build knowledge graph

        Args:
            papers: List of papers to extract from
            download_pdfs: Whether to download PDFs first
            max_papers: Maximum number of papers to process

        Returns:
            KnowledgeGraph with extracted knowledge
        """
        if max_papers:
            papers = papers[:max_papers]

        print(f"\n{'='*60}")
        print(f"🔬 Extraction Pipeline - {len(papers)} papers")
        print(f"Ontology: {self.ontology.name}")
        print(f"{'='*60}\n")

        # Step 1: Add papers to graph
        print("📄 Step 1/5: Adding papers to knowledge graph...")
        for paper in papers:
            self.knowledge_graph.add_paper(paper)
        print(f"✓ Added {len(papers)} papers\n")

        # Step 2: Download PDFs
        if download_pdfs:
            print("📥 Step 2/5: Downloading PDFs...")
            download_results = await self.pdf_downloader.batch_download(papers, max_concurrent=3)
            stats = self.pdf_downloader.get_download_stats(download_results)

            print(f"✓ Downloaded: {stats['successful']}/{stats['total']} papers")
            print(f"  Sources: {stats['by_source']}")
            print(f"  Total size: {stats['total_size_mb']:.1f} MB\n")
        else:
            print("⏭️  Step 2/5: Skipping PDF download\n")

        # Step 3: Extract text
        print("📝 Step 3/5: Extracting text from PDFs...")
        text_results = await self.text_extractor.batch_extract(papers)
        text_stats = self.text_extractor.get_extraction_stats(text_results)

        print(f"✓ Extracted: {text_stats['successful']}/{text_stats['total']} papers")
        print(f"  Avg quality: {text_stats['avg_quality']:.2f}")
        print(f"  Avg words: {text_stats['avg_word_count']}")
        print(f"  With sections: {text_stats['with_sections']}\n")

        # Step 4: Extract entities and relationships
        print("🧠 Step 4/5: Extracting knowledge (entities & relationships)...")
        extraction_results = []

        for i, paper in enumerate(papers):
            if not paper.text_extracted:
                continue

            print(f"  Processing paper {i+1}/{len(papers)}: {paper.short_title}...", end="")

            try:
                # Extract from sections if available, otherwise from full text
                if paper.structured_text:
                    # Use key sections only
                    key_sections = self.text_extractor.extract_key_sections(paper.full_text)
                    result = await self.extractor.extract_from_sections(paper, key_sections)
                else:
                    result = await self.extractor.extract_entities(paper)

                # Extract relationships
                relationships = await self.extractor.extract_relationships(
                    paper, result.entities
                )
                result.relationships = relationships
                result.compute_statistics()

                extraction_results.append(result)

                # Add to knowledge graph
                self.knowledge_graph.add_extraction_result(result)

                print(f" ✓ ({len(result.entities)} entities, {len(result.relationships)} relationships)")

            except Exception as e:
                print(f" ✗ Error: {e}")

        print(f"\n✓ Extracted knowledge from {len(extraction_results)} papers\n")

        # Step 5: Post-processing
        print("🔗 Step 5/5: Post-processing knowledge graph...")

        # Merge similar entities
        print("  Merging similar entities...")
        self.knowledge_graph.merge_similar_entities(similarity_threshold=0.85)

        print("✓ Knowledge graph ready!\n")

        # Print final statistics
        stats = self.knowledge_graph.get_statistics()
        print(f"{'='*60}")
        print("📊 Final Statistics:")
        print(f"{'='*60}")
        print(f"Papers: {stats['papers']['total_papers']}")
        print(f"Entities: {stats['entities']['total_entities']}")
        for entity_type, count in stats['entities']['by_type'].items():
            print(f"  - {entity_type}: {count}")
        print(f"Relationships: {stats['relationships']['total_relationships']}")
        for rel_type, count in stats['relationships']['by_type'].items():
            print(f"  - {rel_type}: {count}")
        print(f"{'='*60}\n")

        return self.knowledge_graph

    async def extract_from_paper_ids(
        self, paper_ids: List[str], papers_dict: Dict[str, Paper], download_pdfs: bool = True
    ) -> KnowledgeGraph:
        """Extract from papers by ID.

        Args:
            paper_ids: List of paper IDs
            papers_dict: Dict mapping paper_id to Paper
            download_pdfs: Whether to download PDFs

        Returns:
            KnowledgeGraph
        """
        papers = [papers_dict[pid] for pid in paper_ids if pid in papers_dict]
        return await self.extract_from_papers(papers, download_pdfs=download_pdfs)

    def save_graph(self, output_path: str):
        """Save knowledge graph to file.

        Args:
            output_path: Output file path
        """
        self.knowledge_graph.save(output_path)
        print(f"✓ Saved knowledge graph to {output_path}")

    def export_for_visualization(self, output_dir: str):
        """Export graph for visualization tools.

        Args:
            output_dir: Output directory
        """
        self.knowledge_graph.export_for_gephi(output_dir)

    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get summary of extraction results.

        Returns:
            Summary dictionary
        """
        stats = self.knowledge_graph.get_statistics()

        return {
            "timestamp": datetime.now().isoformat(),
            "ontology": {
                "name": self.ontology.name,
                "entity_types": [et.name for et in self.ontology.entity_types],
                "relationship_types": [rt.name for rt in self.ontology.relationship_types],
            },
            "statistics": stats,
        }
