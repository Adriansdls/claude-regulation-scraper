"""Data models for research papers."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class PaperSource(str, Enum):
    """Source of paper metadata."""

    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    MANUAL = "manual"
    WEB_SEARCH = "web_search"


class Author(BaseModel):
    """Research paper author."""

    name: str
    author_id: Optional[str] = None  # External ID (e.g., Semantic Scholar)
    affiliation: Optional[str] = None
    email: Optional[str] = None
    h_index: Optional[int] = None
    citation_count: Optional[int] = None

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Author):
            return False
        return self.name == other.name


class Citation(BaseModel):
    """Citation relationship between papers."""

    citing_paper_id: str  # Paper that cites
    cited_paper_id: str  # Paper being cited
    context: Optional[str] = None  # Citation context/sentence
    is_influential: bool = False  # High-importance citation


class PaperMetadata(BaseModel):
    """Extended metadata for a paper."""

    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    pmc_id: Optional[str] = None
    isbn: Optional[str] = None

    # Publication details
    venue: Optional[str] = None  # Journal/conference name
    venue_type: Optional[str] = None  # journal, conference, workshop, preprint
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    # URLs and access
    pdf_url: Optional[HttpUrl] = None
    html_url: Optional[HttpUrl] = None
    is_open_access: bool = False

    # Metrics
    citation_count: int = 0
    reference_count: int = 0
    influential_citation_count: int = 0
    citation_velocity: Optional[float] = None  # Citations per year

    # Fields and topics
    fields_of_study: List[str] = Field(default_factory=list)
    s2_fields: Dict[str, float] = Field(default_factory=dict)  # Semantic Scholar fields


class Paper(BaseModel):
    """Core research paper model."""

    # Primary identifiers
    paper_id: str  # Unique internal ID
    external_ids: Dict[str, str] = Field(default_factory=dict)  # DOI, arXiv, etc.

    # Core information
    title: str
    abstract: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    year: Optional[int] = None
    publication_date: Optional[datetime] = None

    # Content
    full_text: Optional[str] = None  # Extracted text from PDF
    structured_text: Optional[Dict[str, str]] = None  # {section: content}

    # Relationships
    references: List[str] = Field(default_factory=list)  # Paper IDs this paper cites
    cited_by: List[str] = Field(default_factory=list)  # Paper IDs citing this paper

    # Metadata
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    source: PaperSource = PaperSource.MANUAL

    # Discovery tracking
    discovered_at: datetime = Field(default_factory=datetime.now)
    discovered_via: Optional[str] = None  # How we found this paper
    relevance_score: Optional[float] = None  # 0-1 relevance to research question
    relevance_reasoning: Optional[str] = None  # Why it's relevant

    # Processing status
    has_pdf: bool = False
    pdf_path: Optional[str] = None
    text_extracted: bool = False
    extracted_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def __hash__(self):
        return hash(self.paper_id)

    def __eq__(self, other):
        if not isinstance(other, Paper):
            return False
        return self.paper_id == other.paper_id

    @property
    def primary_doi(self) -> Optional[str]:
        """Get DOI from either external_ids or metadata."""
        return self.external_ids.get("DOI") or self.metadata.doi

    @property
    def primary_arxiv_id(self) -> Optional[str]:
        """Get arXiv ID."""
        return self.external_ids.get("ArXiv") or self.metadata.arxiv_id

    @property
    def short_title(self, max_length: int = 50) -> str:
        """Get shortened title for display."""
        if len(self.title) <= max_length:
            return self.title
        return self.title[: max_length - 3] + "..."

    @property
    def author_names(self) -> List[str]:
        """Get list of author names."""
        return [author.name for author in self.authors]

    @property
    def first_author(self) -> Optional[Author]:
        """Get first author."""
        return self.authors[0] if self.authors else None

    def to_citation_string(self) -> str:
        """Generate citation string (simple format)."""
        authors = ", ".join(self.author_names[:3])
        if len(self.authors) > 3:
            authors += " et al."
        year = f"({self.year})" if self.year else ""
        return f"{authors} {year}. {self.title}"

    def update_from_external(self, data: Dict[str, Any], source: PaperSource):
        """Update paper with data from external source."""
        self.source = source

        # Update basic fields if not set
        if not self.title and "title" in data:
            self.title = data["title"]
        if not self.abstract and "abstract" in data:
            self.abstract = data["abstract"]
        if not self.year and "year" in data:
            self.year = data["year"]

        # Merge authors
        if "authors" in data and not self.authors:
            self.authors = [
                Author(name=a.get("name", ""), author_id=a.get("authorId"))
                for a in data["authors"]
            ]

        # Merge external IDs
        if "externalIds" in data:
            self.external_ids.update(data["externalIds"])

        # Update metadata
        if "citationCount" in data:
            self.metadata.citation_count = data["citationCount"]
        if "referenceCount" in data:
            self.metadata.reference_count = data["referenceCount"]
        if "fieldsOfStudy" in data:
            self.metadata.fields_of_study = data["fieldsOfStudy"]
        if "venue" in data:
            self.metadata.venue = data["venue"]
        if "isOpenAccess" in data:
            self.metadata.is_open_access = data["isOpenAccess"]
        if "openAccessPdf" in data and data["openAccessPdf"]:
            self.metadata.pdf_url = data["openAccessPdf"].get("url")
