"""
Extraction result and metadata models
Defines data structures for extraction processes and results
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator
from uuid import UUID, uuid4

from .regulation_models import DocumentType, Jurisdiction


class ExtractionStatus(str, Enum):
    """Status of extraction processes"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class ExtractionMethod(str, Enum):
    """Methods used for content extraction"""
    HTML_PARSING = "html_parsing"
    PDF_EXTRACTION = "pdf_extraction"
    OCR = "ocr"
    COMPUTER_VISION = "computer_vision"
    API = "api"
    MANUAL = "manual"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    """Types of extracted content"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"
    FORM = "form"
    CHART = "chart"
    DIAGRAM = "diagram"
    OTHER = "other"


class QualityLevel(str, Enum):
    """Quality levels for extracted content"""
    EXCELLENT = "excellent"  # >95% confidence
    GOOD = "good"           # 80-95% confidence
    FAIR = "fair"           # 60-80% confidence
    POOR = "poor"           # <60% confidence


class WebsiteProfile(BaseModel):
    """Profile of a website analyzed for extraction"""
    domain: str = Field(..., description="Website domain")
    base_url: HttpUrl = Field(..., description="Base URL")
    title: Optional[str] = Field(None, description="Website title")
    
    # Technical characteristics
    has_semantic_markup: bool = Field(default=False, description="Has semantic HTML markup")
    js_dependent: bool = Field(default=False, description="Requires JavaScript for content")
    uses_spa: bool = Field(default=False, description="Single Page Application")
    pdf_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of PDF content")
    has_complex_tables: bool = Field(default=False, description="Contains complex table structures")
    has_forms: bool = Field(default=False, description="Contains forms")
    
    # Content characteristics
    content_types: Dict[ContentType, float] = Field(default_factory=dict, description="Content type distribution")
    estimated_documents: Optional[int] = Field(None, description="Estimated number of documents")
    
    # Language and accessibility
    language: str = Field(default="en", description="Primary language")
    languages: List[str] = Field(default_factory=list, description="All detected languages")
    accessibility_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Accessibility compliance score")
    
    # Legal framework
    jurisdiction: Optional[Jurisdiction] = Field(None, description="Detected jurisdiction")
    legal_framework: Optional[str] = Field(None, description="Legal system type")
    document_types: List[DocumentType] = Field(default_factory=list, description="Document types found")
    
    # Technical details
    robots_allowed: bool = Field(default=True, description="Robots.txt allows scraping")
    rate_limit_info: Optional[Dict[str, Any]] = Field(None, description="Rate limiting information")
    last_updated: Optional[datetime] = Field(None, description="When site was last updated")
    
    # Analysis metadata
    profiled_at: datetime = Field(default_factory=datetime.utcnow, description="When profile was created")
    profile_version: str = Field(default="1.0", description="Profile schema version")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Profile accuracy confidence")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExtractionJob(BaseModel):
    """Job for extracting content from a source"""
    id: UUID = Field(default_factory=uuid4, description="Job ID")
    url: HttpUrl = Field(..., description="Source URL")
    
    # Job configuration
    extraction_methods: List[ExtractionMethod] = Field(..., description="Methods to use for extraction")
    target_content: List[str] = Field(default_factory=list, description="Specific content to extract")
    max_documents: Optional[int] = Field(None, description="Maximum documents to extract")
    
    # Status tracking
    status: ExtractionStatus = Field(default=ExtractionStatus.PENDING, description="Current status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Completion progress")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    
    # Metadata
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=highest)")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries allowed")
    
    # Results
    extracted_documents: List[UUID] = Field(default_factory=list, description="IDs of extracted documents")
    error_messages: List[str] = Field(default_factory=list, description="Error messages")
    
    # Configuration
    user_agent: Optional[str] = Field(None, description="User agent string")
    request_delay: float = Field(default=1.0, ge=0.0, description="Delay between requests (seconds)")
    timeout: int = Field(default=30, ge=1, description="Request timeout (seconds)")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }
    
    def add_error(self, error: str):
        """Add an error message"""
        self.error_messages.append(f"{datetime.utcnow().isoformat()}: {error}")
    
    def is_completed(self) -> bool:
        """Check if job is completed"""
        return self.status in [ExtractionStatus.COMPLETED, ExtractionStatus.FAILED, ExtractionStatus.CANCELLED]
    
    def duration_seconds(self) -> Optional[int]:
        """Get job duration in seconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class ExtractedContent(BaseModel):
    """Individual piece of extracted content"""
    id: UUID = Field(default_factory=uuid4, description="Content ID")
    job_id: UUID = Field(..., description="Parent job ID")
    
    # Content details
    content_type: ContentType = Field(..., description="Type of content")
    raw_content: str = Field(..., description="Raw extracted content")
    processed_content: Optional[str] = Field(None, description="Processed/cleaned content")
    
    # Source information
    source_url: HttpUrl = Field(..., description="Source URL")
    source_element: Optional[str] = Field(None, description="Source HTML element or PDF page")
    xpath: Optional[str] = Field(None, description="XPath if from HTML")
    bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates [x1,y1,x2,y2]")
    
    # Extraction metadata
    extraction_method: ExtractionMethod = Field(..., description="Method used for extraction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    quality: QualityLevel = Field(..., description="Quality assessment")
    
    # Processing information
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    agent_id: Optional[str] = Field(None, description="ID of agent that extracted this")
    
    # Content attributes
    language: Optional[str] = Field(None, description="Content language")
    word_count: Optional[int] = Field(None, description="Word count")
    character_count: Optional[int] = Field(None, description="Character count")
    
    # Relationships
    parent_content_id: Optional[UUID] = Field(None, description="Parent content if hierarchical")
    related_content_ids: List[UUID] = Field(default_factory=list, description="Related content pieces")
    
    # Quality indicators
    has_errors: bool = Field(default=False, description="Whether extraction had errors")
    error_details: List[str] = Field(default_factory=list, description="Specific errors encountered")
    validation_flags: List[str] = Field(default_factory=list, description="Validation warnings")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence score"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def get_quality_score(self) -> float:
        """Get numeric quality score"""
        quality_scores = {
            QualityLevel.EXCELLENT: 0.95,
            QualityLevel.GOOD: 0.85,
            QualityLevel.FAIR: 0.70,
            QualityLevel.POOR: 0.50
        }
        return quality_scores.get(self.quality, 0.0)


class ExtractionSummary(BaseModel):
    """Summary of extraction job results"""
    job_id: UUID = Field(..., description="Job ID")
    
    # Counts
    total_content_pieces: int = Field(default=0, description="Total pieces of content extracted")
    documents_created: int = Field(default=0, description="Number of regulation documents created")
    
    # Content type breakdown
    content_breakdown: Dict[ContentType, int] = Field(default_factory=dict, description="Content by type")
    
    # Quality metrics
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    quality_distribution: Dict[QualityLevel, int] = Field(default_factory=dict, description="Quality distribution")
    
    # Performance metrics
    total_processing_time: float = Field(default=0.0, description="Total processing time in seconds")
    average_processing_time: float = Field(default=0.0, description="Average time per content piece")
    
    # Error summary
    total_errors: int = Field(default=0, description="Total number of errors")
    error_rate: float = Field(default=0.0, description="Error rate (0-1)")
    common_errors: List[str] = Field(default_factory=list, description="Most common error types")
    
    # Success metrics
    success_rate: float = Field(default=0.0, description="Overall success rate")
    completeness_score: float = Field(default=0.0, description="Completeness of extraction")
    
    class Config:
        use_enum_values = True
        json_encoders = {UUID: str}


class ContentQuality(BaseModel):
    """Quality assessment for extracted content"""
    content_id: UUID = Field(..., description="Content ID being assessed")
    
    # Quality scores
    overall_quality: QualityLevel = Field(..., description="Overall quality level")
    accuracy_score: float = Field(..., ge=0.0, le=1.0, description="Accuracy assessment")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Completeness assessment") 
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to regulations")
    
    # Quality indicators
    has_structure: bool = Field(default=False, description="Content has clear structure")
    has_references: bool = Field(default=False, description="Contains legal references")
    proper_formatting: bool = Field(default=False, description="Properly formatted text")
    
    # Issues found
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    
    # Assessment metadata
    assessed_at: datetime = Field(default_factory=datetime.utcnow, description="Assessment timestamp")
    assessor_id: Optional[str] = Field(None, description="ID of assessing agent")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ValidationResult(BaseModel):
    """Result of content validation"""
    content_id: UUID = Field(..., description="Content ID being validated")
    
    # Validation status
    is_valid: bool = Field(..., description="Whether content passed validation")
    validation_score: float = Field(..., ge=0.0, le=1.0, description="Overall validation score")
    
    # Validation checks
    structural_validation: bool = Field(default=False, description="Structure validation passed")
    content_validation: bool = Field(default=False, description="Content validation passed")
    format_validation: bool = Field(default=False, description="Format validation passed")
    legal_validation: bool = Field(default=False, description="Legal content validation passed")
    
    # Validation details
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors found")
    validation_warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    validation_suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    
    # Legal compliance
    regulation_indicators: List[str] = Field(default_factory=list, description="Found regulation indicators")
    legal_references: List[str] = Field(default_factory=list, description="Found legal references")
    jurisdiction_match: bool = Field(default=False, description="Matches expected jurisdiction")
    
    # Validation metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    validator_id: Optional[str] = Field(None, description="ID of validating agent")
    validation_method: str = Field(default="llm_analysis", description="Method used for validation")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AgentMetrics(BaseModel):
    """Performance metrics for extraction agents"""
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: str = Field(..., description="Type of agent")
    
    # Performance metrics
    jobs_processed: int = Field(default=0, description="Total jobs processed")
    content_extracted: int = Field(default=0, description="Total content pieces extracted")
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    success_rate: float = Field(default=0.0, description="Success rate")
    
    # Timing metrics
    average_processing_time: float = Field(default=0.0, description="Average processing time")
    total_processing_time: float = Field(default=0.0, description="Total processing time")
    
    # Quality metrics
    quality_scores: Dict[QualityLevel, int] = Field(default_factory=dict, description="Quality distribution")
    error_rate: float = Field(default=0.0, description="Error rate")
    
    # Resource usage
    memory_usage: Optional[float] = Field(None, description="Peak memory usage (MB)")
    cpu_usage: Optional[float] = Field(None, description="Average CPU usage (%)")
    
    # Last activity
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }