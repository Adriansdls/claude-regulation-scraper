"""
Core regulation data models
Defines data structures for regulations, legal documents, and related entities
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator
from uuid import UUID, uuid4


class DocumentType(str, Enum):
    """Types of legal documents"""
    LEGISLATION = "legislation"
    REGULATION = "regulation"
    BILL = "bill"
    ACT = "act"
    DIRECTIVE = "directive"
    AMENDMENT = "amendment"
    PROPOSAL = "proposal"
    CONSULTATION = "consultation"
    GUIDANCE = "guidance"
    CASE_LAW = "case_law"
    TREATY = "treaty"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Status of legal documents"""
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ENACTED = "enacted"
    IN_FORCE = "in_force"
    AMENDED = "amended"
    REPEALED = "repealed"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class Jurisdiction(str, Enum):
    """Legal jurisdictions"""
    UK = "uk"
    EU = "eu"
    US = "us"
    CANADA = "canada"
    AUSTRALIA = "australia"
    NEW_ZEALAND = "new_zealand"
    INTERNATIONAL = "international"
    OTHER = "other"


class LegalAuthority(BaseModel):
    """Legal authority/institution that issued the document"""
    name: str = Field(..., description="Name of the authority")
    type: str = Field(..., description="Type of authority (ministry, parliament, court, etc.)")
    jurisdiction: Jurisdiction = Field(..., description="Jurisdiction of authority")
    website: Optional[HttpUrl] = Field(None, description="Official website")
    contact_info: Optional[Dict[str, str]] = Field(None, description="Contact information")


class DocumentIdentifier(BaseModel):
    """Official identifiers for legal documents"""
    primary_id: str = Field(..., description="Primary official identifier")
    secondary_ids: List[str] = Field(default_factory=list, description="Alternative identifiers")
    citation: Optional[str] = Field(None, description="Standard legal citation")
    isbn: Optional[str] = Field(None, description="ISBN if applicable")
    issn: Optional[str] = Field(None, description="ISSN if applicable")
    doi: Optional[str] = Field(None, description="DOI if applicable")


class DocumentMetadata(BaseModel):
    """Metadata about the document"""
    language: str = Field(default="en", description="Primary language")
    languages: List[str] = Field(default_factory=list, description="All available languages")
    page_count: Optional[int] = Field(None, description="Number of pages")
    word_count: Optional[int] = Field(None, description="Approximate word count")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    format: Optional[str] = Field(None, description="File format (PDF, HTML, XML, etc.)")
    encoding: Optional[str] = Field(None, description="Character encoding")
    checksum: Optional[str] = Field(None, description="File checksum for integrity")


class DateInfo(BaseModel):
    """Date-related information for legal documents"""
    created: Optional[datetime] = Field(None, description="Document creation date")
    published: Optional[date] = Field(None, description="Publication date")
    effective_date: Optional[date] = Field(None, description="Date when document becomes effective")
    last_modified: Optional[datetime] = Field(None, description="Last modification date")
    expiry_date: Optional[date] = Field(None, description="Expiry date if applicable")
    review_date: Optional[date] = Field(None, description="Scheduled review date")


class DocumentStructure(BaseModel):
    """Hierarchical structure of the document"""
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Document sections")
    chapters: List[Dict[str, Any]] = Field(default_factory=list, description="Document chapters") 
    articles: List[Dict[str, Any]] = Field(default_factory=list, description="Articles")
    paragraphs: List[Dict[str, Any]] = Field(default_factory=list, description="Paragraphs")
    annexes: List[Dict[str, Any]] = Field(default_factory=list, description="Annexes/appendices")
    definitions: Dict[str, str] = Field(default_factory=dict, description="Term definitions")
    references: List[str] = Field(default_factory=list, description="References to other documents")


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process"""
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    extraction_method: str = Field(..., description="Method used for extraction")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction accuracy")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    agent_version: Optional[str] = Field(None, description="Version of extraction agent")
    source_url: HttpUrl = Field(..., description="Source URL where document was found")
    source_domain: str = Field(..., description="Source domain")
    last_checked: Optional[datetime] = Field(None, description="When source was last checked")


class Regulation(BaseModel):
    """Core regulation/legal document model"""
    
    # Core identification
    id: UUID = Field(default_factory=uuid4, description="Unique internal ID")
    title: str = Field(..., description="Document title")
    document_type: DocumentType = Field(..., description="Type of document")
    status: DocumentStatus = Field(..., description="Current status")
    
    # Official identifiers
    identifiers: DocumentIdentifier = Field(..., description="Official identifiers")
    
    # Authority and jurisdiction
    authority: LegalAuthority = Field(..., description="Issuing authority")
    jurisdiction: Jurisdiction = Field(..., description="Legal jurisdiction")
    
    # Content
    abstract: Optional[str] = Field(None, description="Document summary/abstract")
    full_text: Optional[str] = Field(None, description="Full document text")
    key_provisions: List[str] = Field(default_factory=list, description="Key regulatory provisions")
    
    # Structure
    structure: Optional[DocumentStructure] = Field(None, description="Document structure")
    
    # Dates
    dates: DateInfo = Field(..., description="Document dates")
    
    # Metadata
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    extraction: ExtractionMetadata = Field(..., description="Extraction metadata")
    
    # Relationships
    parent_documents: List[str] = Field(default_factory=list, description="Parent/enabling legislation")
    child_documents: List[str] = Field(default_factory=list, description="Subsidiary regulations")
    related_documents: List[str] = Field(default_factory=list, description="Related documents")
    superseded_by: Optional[str] = Field(None, description="Document that supersedes this one")
    supersedes: Optional[str] = Field(None, description="Document that this supersedes")
    
    # Topics and classification
    topics: List[str] = Field(default_factory=list, description="Subject matter topics")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    classification_codes: List[str] = Field(default_factory=list, description="Official classification codes")
    
    # Quality metrics
    completeness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Data completeness score")
    quality_flags: List[str] = Field(default_factory=list, description="Quality issues identified")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: str
        }
        
    @field_validator('full_text')
    @classmethod
    def validate_text_length(cls, v):
        """Validate text length"""
        if v and len(v) > 10_000_000:  # 10MB limit
            raise ValueError("Full text exceeds maximum length")
        return v
    
    
    def add_quality_flag(self, flag: str):
        """Add a quality flag"""
        if flag not in self.quality_flags:
            self.quality_flags.append(flag)
    
    def get_display_title(self) -> str:
        """Get formatted display title"""
        if self.identifiers.primary_id:
            return f"{self.identifiers.primary_id}: {self.title}"
        return self.title
    
    def is_current(self) -> bool:
        """Check if document is currently in force"""
        return self.status in [DocumentStatus.IN_FORCE, DocumentStatus.ENACTED]
    
    def has_expired(self) -> bool:
        """Check if document has expired"""
        if self.dates.expiry_date:
            return self.dates.expiry_date < date.today()
        return False


class RegulationCollection(BaseModel):
    """Collection of related regulations"""
    id: UUID = Field(default_factory=uuid4, description="Collection ID")
    name: str = Field(..., description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    regulations: List[UUID] = Field(default_factory=list, description="Regulation IDs in collection")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Collection creation date")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update date")
    tags: List[str] = Field(default_factory=list, description="Collection tags")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class RegulationSearchQuery(BaseModel):
    """Model for regulation search queries"""
    query: str = Field(..., description="Search query")
    document_types: Optional[List[DocumentType]] = Field(None, description="Filter by document types")
    jurisdictions: Optional[List[Jurisdiction]] = Field(None, description="Filter by jurisdictions") 
    authorities: Optional[List[str]] = Field(None, description="Filter by authorities")
    date_from: Optional[date] = Field(None, description="Date range start")
    date_to: Optional[date] = Field(None, description="Date range end")
    topics: Optional[List[str]] = Field(None, description="Filter by topics")
    status: Optional[List[DocumentStatus]] = Field(None, description="Filter by status")
    limit: int = Field(default=20, ge=1, le=100, description="Result limit")
    offset: int = Field(default=0, ge=0, description="Result offset")
    
    class Config:
        use_enum_values = True


class RegulationSearchResult(BaseModel):
    """Search result for regulations"""
    regulation: Regulation = Field(..., description="The regulation")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    highlights: List[str] = Field(default_factory=list, description="Highlighted text snippets")
    matched_fields: List[str] = Field(default_factory=list, description="Fields that matched the query")


class RegulationSearchResponse(BaseModel):
    """Response for regulation search"""
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results")
    results: List[RegulationSearchResult] = Field(..., description="Search results")
    took_ms: int = Field(..., description="Query time in milliseconds")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    suggestions: List[str] = Field(default_factory=list, description="Search suggestions")