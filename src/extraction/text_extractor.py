"""Extract text from PDFs with multiple strategies and quality assessment."""

import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import fitz  # PyMuPDF
import pdfplumber

from ..models.paper import Paper


class TextExtractionResult:
    """Result of text extraction."""

    def __init__(
        self,
        success: bool,
        full_text: Optional[str] = None,
        structured_text: Optional[Dict[str, str]] = None,
        method: Optional[str] = None,
        quality_score: float = 0.0,
        word_count: int = 0,
        has_sections: bool = False,
        error: Optional[str] = None,
    ):
        self.success = success
        self.full_text = full_text
        self.structured_text = structured_text or {}
        self.method = method
        self.quality_score = quality_score
        self.word_count = word_count
        self.has_sections = has_sections
        self.error = error


class TextExtractor:
    """Extract and parse text from PDF files."""

    # Common academic paper section headers
    SECTION_PATTERNS = {
        "abstract": r"(?i)^abstract\s*$",
        "introduction": r"(?i)^(introduction|1\.?\s+introduction)\s*$",
        "related_work": r"(?i)^(related\s+work|background|literature\s+review|2\.?\s+)",
        "methods": r"(?i)^(methods?|methodology|approach|3\.?\s+)",
        "experiments": r"(?i)^(experiments?|experimental\s+setup|evaluation|4\.?\s+)",
        "results": r"(?i)^(results?|findings|5\.?\s+)",
        "discussion": r"(?i)^(discussion|analysis|6\.?\s+)",
        "conclusion": r"(?i)^(conclusions?|concluding\s+remarks|7\.?\s+)",
        "references": r"(?i)^(references|bibliography)\s*$",
    }

    def __init__(self):
        pass

    async def extract_text(self, pdf_path: str) -> TextExtractionResult:
        """Extract text from PDF using best available method.

        Tries multiple methods:
        1. PyMuPDF (fast, good for most PDFs)
        2. pdfplumber (better for tables and structure)
        3. OCR fallback (for scanned documents) - future

        Args:
            pdf_path: Path to PDF file

        Returns:
            TextExtractionResult
        """
        path = Path(pdf_path)
        if not path.exists():
            return TextExtractionResult(success=False, error="PDF file not found")

        # Try PyMuPDF first
        result = await self._extract_with_pymupdf(path)
        if result.success and result.quality_score >= 0.7:
            return result

        # Try pdfplumber if PyMuPDF quality is low
        result2 = await self._extract_with_pdfplumber(path)
        if result2.success and result2.quality_score > result.quality_score:
            return result2

        # Return best result
        return result if result.quality_score > result2.quality_score else result2

    async def _extract_with_pymupdf(self, pdf_path: Path) -> TextExtractionResult:
        """Extract text using PyMuPDF.

        Args:
            pdf_path: Path to PDF

        Returns:
            TextExtractionResult
        """
        try:
            doc = fitz.open(pdf_path)

            # Extract text from all pages
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            doc.close()

            # Clean text
            full_text = self._clean_text(full_text)

            # Assess quality
            quality = self._assess_quality(full_text)

            # Parse structure
            structured = self._parse_sections(full_text)

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                structured_text=structured,
                method="pymupdf",
                quality_score=quality,
                word_count=len(full_text.split()),
                has_sections=len(structured) > 1,
            )

        except Exception as e:
            return TextExtractionResult(success=False, error=f"PyMuPDF extraction failed: {e}")

    async def _extract_with_pdfplumber(self, pdf_path: Path) -> TextExtractionResult:
        """Extract text using pdfplumber.

        Args:
            pdf_path: Path to PDF

        Returns:
            TextExtractionResult
        """
        try:
            full_text = ""

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

            # Clean text
            full_text = self._clean_text(full_text)

            # Assess quality
            quality = self._assess_quality(full_text)

            # Parse structure
            structured = self._parse_sections(full_text)

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                structured_text=structured,
                method="pdfplumber",
                quality_score=quality,
                word_count=len(full_text.split()),
                has_sections=len(structured) > 1,
            )

        except Exception as e:
            return TextExtractionResult(success=False, error=f"pdfplumber extraction failed: {e}")

    def _clean_text(self, text: str) -> str:
        """Clean extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove page numbers (common pattern: single number on a line)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

        # Remove hyphenation at line breaks
        text = re.sub(r"-\s*\n\s*", "", text)

        # Normalize newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _assess_quality(self, text: str) -> float:
        """Assess text extraction quality.

        Args:
            text: Extracted text

        Returns:
            Quality score 0-1
        """
        if not text:
            return 0.0

        score = 1.0

        # Check length
        word_count = len(text.split())
        if word_count < 100:
            score -= 0.5  # Very short, likely incomplete
        elif word_count < 500:
            score -= 0.2

        # Check for common academic paper indicators
        academic_indicators = [
            "abstract",
            "introduction",
            "method",
            "results",
            "conclusion",
            "references",
        ]
        found_indicators = sum(1 for ind in academic_indicators if ind in text.lower())
        if found_indicators < 2:
            score -= 0.3

        # Check for garbled text (too many non-alphanumeric characters)
        alpha_ratio = sum(c.isalnum() or c.isspace() for c in text) / len(text)
        if alpha_ratio < 0.7:
            score -= 0.4

        # Check for repeated characters (sign of OCR errors)
        if re.search(r"(.)\1{5,}", text):
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse text into sections.

        Args:
            text: Full text

        Returns:
            Dict mapping section names to content
        """
        sections = {}

        # Split into lines
        lines = text.split("\n")

        current_section = "preamble"
        current_content = []

        for line in lines:
            line = line.strip()

            # Check if this line is a section header
            matched_section = None
            for section_name, pattern in self.SECTION_PATTERNS.items():
                if re.match(pattern, line):
                    matched_section = section_name
                    break

            if matched_section:
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = matched_section
                current_content = []
            else:
                # Add to current section
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from full text.

        Args:
            text: Full text

        Returns:
            Abstract text or None
        """
        # Try structured sections first
        sections = self._parse_sections(text)
        if "abstract" in sections:
            return sections["abstract"]

        # Fallback: look for abstract marker
        pattern = r"abstract\s*(.{100,2000}?)\s*(introduction|1\.|\n\n)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        return None

    def extract_key_sections(self, text: str) -> Dict[str, str]:
        """Extract key sections for extraction.

        Focuses on sections most likely to contain entities/relationships:
        - Abstract
        - Introduction
        - Methods
        - Results
        - Conclusion

        Args:
            text: Full text

        Returns:
            Dict of key sections
        """
        all_sections = self._parse_sections(text)

        key_section_names = ["abstract", "introduction", "methods", "results", "conclusion"]

        key_sections = {}
        for name in key_section_names:
            if name in all_sections:
                key_sections[name] = all_sections[name]

        # If we don't have any key sections, use first 5000 chars
        if not key_sections:
            key_sections["full_text_preview"] = text[:5000]

        return key_sections

    async def batch_extract(self, papers: List[Paper]) -> Dict[str, TextExtractionResult]:
        """Extract text from multiple papers.

        Args:
            papers: List of papers with pdf_path set

        Returns:
            Dict mapping paper_id to TextExtractionResult
        """
        results = {}

        for paper in papers:
            if not paper.pdf_path:
                results[paper.paper_id] = TextExtractionResult(
                    success=False, error="No PDF path"
                )
                continue

            result = await self.extract_text(paper.pdf_path)
            results[paper.paper_id] = result

            # Update paper object
            if result.success:
                paper.full_text = result.full_text
                paper.structured_text = result.structured_text
                paper.text_extracted = True

        return results

    def get_extraction_stats(self, results: Dict[str, TextExtractionResult]) -> Dict:
        """Get statistics about extraction results.

        Args:
            results: Dict of extraction results

        Returns:
            Statistics dict
        """
        total = len(results)
        successful = sum(1 for r in results.values() if r.success)

        avg_quality = (
            sum(r.quality_score for r in results.values() if r.success) / successful
            if successful > 0
            else 0
        )

        avg_word_count = (
            sum(r.word_count for r in results.values() if r.success) / successful
            if successful > 0
            else 0
        )

        with_sections = sum(1 for r in results.values() if r.success and r.has_sections)

        # Method distribution
        by_method = {}
        for result in results.values():
            if result.success and result.method:
                by_method[result.method] = by_method.get(result.method, 0) + 1

        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_quality": avg_quality,
            "avg_word_count": int(avg_word_count),
            "with_sections": with_sections,
            "by_method": by_method,
        }
