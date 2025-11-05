"""
Pydantic/JSON schemas for data validation
Provides comprehensive validation schemas for all data models
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime, date
import re
from urllib.parse import urlparse


class URLValidator(BaseModel):
    """Validates URLs and extracts information"""
    url: str
    
    @validator('url')
    def validate_url_format(cls, v):
        """Validate URL format"""
        if not v:
            raise ValueError("URL cannot be empty")
        
        try:
            parsed = urlparse(v)
            if not parsed.scheme:
                raise ValueError("URL must include scheme (http/https)")
            if not parsed.netloc:
                raise ValueError("URL must include domain")
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("URL scheme must be http or https")
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")
        
        return v


class TextContentValidator(BaseModel):
    """Validates text content quality and format"""
    content: str
    min_length: int = Field(default=10)
    max_length: int = Field(default=10_000_000)
    
    @validator('content')
    def validate_content_quality(cls, v, values):
        """Validate content meets quality standards"""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        
        # Check length constraints
        min_len = values.get('min_length', 10)
        max_len = values.get('max_length', 10_000_000)
        
        if len(v) < min_len:
            raise ValueError(f"Content too short: minimum {min_len} characters")
        if len(v) > max_len:
            raise ValueError(f"Content too long: maximum {max_len} characters")
        
        # Check for mostly gibberish (very basic check)
        alpha_ratio = sum(c.isalpha() for c in v) / len(v) if v else 0
        if alpha_ratio < 0.1:  # Less than 10% alphabetic characters
            raise ValueError("Content appears to be mostly non-alphabetic")
        
        return v.strip()


class DocumentIdentifierValidator(BaseModel):
    """Validates document identifiers"""
    primary_id: str
    secondary_ids: List[str] = Field(default_factory=list)
    
    @validator('primary_id')
    def validate_primary_id(cls, v):
        """Validate primary identifier format"""
        if not v or not v.strip():
            raise ValueError("Primary ID cannot be empty")
        
        # Remove extra whitespace
        v = v.strip()
        
        # Basic format checks
        if len(v) < 3:
            raise ValueError("Primary ID too short")
        if len(v) > 200:
            raise ValueError("Primary ID too long")
        
        return v
    
    @validator('secondary_ids')
    def validate_secondary_ids(cls, v):
        """Validate secondary identifiers"""
        if not v:
            return []
        
        validated_ids = []
        for id_val in v:
            if id_val and id_val.strip():
                clean_id = id_val.strip()
                if len(clean_id) >= 3 and len(clean_id) <= 200:
                    validated_ids.append(clean_id)
        
        return list(set(validated_ids))  # Remove duplicates


class DateRangeValidator(BaseModel):
    """Validates date ranges"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    @root_validator
    def validate_date_range(cls, values):
        """Validate date range logic"""
        start = values.get('start_date')
        end = values.get('end_date')
        
        if start and end:
            if start > end:
                raise ValueError("Start date cannot be after end date")
            
            # Check for reasonable date ranges
            if (end - start).days > 36500:  # 100 years
                raise ValueError("Date range cannot exceed 100 years")
        
        # Validate dates are not too far in the future
        if start and start > date.today().replace(year=date.today().year + 10):
            raise ValueError("Start date cannot be more than 10 years in the future")
        if end and end > date.today().replace(year=date.today().year + 10):
            raise ValueError("End date cannot be more than 10 years in the future")
        
        return values


class ScoreValidator(BaseModel):
    """Validates score values"""
    score: float
    min_score: float = Field(default=0.0)
    max_score: float = Field(default=1.0)
    
    @validator('score')
    def validate_score_range(cls, v, values):
        """Validate score is within acceptable range"""
        min_val = values.get('min_score', 0.0)
        max_val = values.get('max_score', 1.0)
        
        if not isinstance(v, (int, float)):
            raise ValueError("Score must be a number")
        
        if v < min_val or v > max_val:
            raise ValueError(f"Score must be between {min_val} and {max_val}")
        
        return float(v)


class LanguageCodeValidator(BaseModel):
    """Validates language codes"""
    language: str
    
    # Common ISO 639-1 language codes
    VALID_LANGUAGES = {
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 
        'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'da', 'no',
        'fi', 'cs', 'sk', 'hu', 'ro', 'bg', 'hr', 'sr', 'sl', 'et',
        'lv', 'lt', 'mt', 'ga', 'cy', 'gd', 'eu', 'ca', 'gl', 'is'
    }
    
    @validator('language')
    def validate_language_code(cls, v):
        """Validate language code format"""
        if not v:
            raise ValueError("Language code cannot be empty")
        
        v = v.lower().strip()
        
        # Check format (2-3 letter code)
        if not re.match(r'^[a-z]{2,3}$', v):
            raise ValueError("Language code must be 2-3 lowercase letters")
        
        # Check against known codes (optional - could be made more permissive)
        if v not in cls.VALID_LANGUAGES:
            # Allow it but log a warning
            pass
        
        return v


class ExtractionJobValidator(BaseModel):
    """Validates extraction job configurations"""
    url: str
    max_documents: Optional[int] = None
    request_delay: float = Field(default=1.0)
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL"""
        validator = URLValidator(url=v)
        return validator.url
    
    @validator('max_documents')
    def validate_max_documents(cls, v):
        """Validate document limit"""
        if v is not None:
            if v <= 0:
                raise ValueError("max_documents must be positive")
            if v > 10000:
                raise ValueError("max_documents cannot exceed 10,000")
        return v
    
    @validator('request_delay')
    def validate_request_delay(cls, v):
        """Validate request delay"""
        if v < 0:
            raise ValueError("request_delay cannot be negative")
        if v > 60:
            raise ValueError("request_delay cannot exceed 60 seconds")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout"""
        if v <= 0:
            raise ValueError("timeout must be positive")
        if v > 600:
            raise ValueError("timeout cannot exceed 600 seconds")
        return v
    
    @validator('max_retries')
    def validate_max_retries(cls, v):
        """Validate retry count"""
        if v < 0:
            raise ValueError("max_retries cannot be negative")
        if v > 10:
            raise ValueError("max_retries cannot exceed 10")
        return v


class SearchQueryValidator(BaseModel):
    """Validates search query parameters"""
    query: str
    limit: int = Field(default=20)
    offset: int = Field(default=0)
    
    @validator('query')
    def validate_search_query(cls, v):
        """Validate search query"""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        
        v = v.strip()
        
        if len(v) < 2:
            raise ValueError("Search query must be at least 2 characters")
        if len(v) > 1000:
            raise ValueError("Search query cannot exceed 1000 characters")
        
        # Basic SQL injection prevention
        dangerous_patterns = [
            r';.*--', r'union.*select', r'drop.*table', 
            r'delete.*from', r'insert.*into', r'update.*set'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError("Query contains potentially dangerous patterns")
        
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate result limit"""
        if v <= 0:
            raise ValueError("limit must be positive")
        if v > 100:
            raise ValueError("limit cannot exceed 100")
        return v
    
    @validator('offset')
    def validate_offset(cls, v):
        """Validate result offset"""
        if v < 0:
            raise ValueError("offset cannot be negative")
        if v > 10000:
            raise ValueError("offset cannot exceed 10,000")
        return v


class RegulationDataValidator(BaseModel):
    """Comprehensive validation for regulation data"""
    title: str
    identifiers: Dict[str, Any]
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('title')
    def validate_title(cls, v):
        """Validate regulation title"""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        
        v = v.strip()
        
        if len(v) < 5:
            raise ValueError("Title too short")
        if len(v) > 500:
            raise ValueError("Title too long")
        
        return v
    
    @validator('identifiers')
    def validate_identifiers(cls, v):
        """Validate identifier structure"""
        if not v:
            raise ValueError("Identifiers cannot be empty")
        
        if 'primary_id' not in v:
            raise ValueError("primary_id is required in identifiers")
        
        # Validate primary ID
        validator = DocumentIdentifierValidator(
            primary_id=v['primary_id'],
            secondary_ids=v.get('secondary_ids', [])
        )
        
        return v
    
    @validator('content')
    def validate_content(cls, v):
        """Validate content if provided"""
        if v:
            validator = TextContentValidator(content=v)
            return validator.content
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata structure"""
        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")
        
        # Validate specific metadata fields if present
        if 'language' in v:
            lang_validator = LanguageCodeValidator(language=v['language'])
            v['language'] = lang_validator.language
        
        if 'confidence_score' in v:
            score_validator = ScoreValidator(score=v['confidence_score'])
            v['confidence_score'] = score_validator.score
        
        return v


class BatchValidationResult(BaseModel):
    """Result of batch validation operation"""
    total_items: int = Field(..., description="Total items validated")
    valid_items: int = Field(..., description="Number of valid items")
    invalid_items: int = Field(..., description="Number of invalid items")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Validation errors")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Validation warnings")
    success_rate: float = Field(..., description="Validation success rate")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def validate_regulation_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate regulation data and return cleaned data
    
    Args:
        data: Raw regulation data dictionary
        
    Returns:
        Validated and cleaned data dictionary
        
    Raises:
        ValueError: If validation fails
    """
    try:
        validator = RegulationDataValidator(**data)
        return validator.dict()
    except Exception as e:
        raise ValueError(f"Regulation data validation failed: {e}")


def validate_extraction_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extraction job configuration
    
    Args:
        data: Raw job configuration dictionary
        
    Returns:
        Validated job configuration
        
    Raises:
        ValueError: If validation fails
    """
    try:
        validator = ExtractionJobValidator(**data)
        return validator.dict()
    except Exception as e:
        raise ValueError(f"Extraction job validation failed: {e}")


def validate_search_query(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate search query parameters
    
    Args:
        data: Raw search query parameters
        
    Returns:
        Validated search parameters
        
    Raises:
        ValueError: If validation fails
    """
    try:
        validator = SearchQueryValidator(**data)
        return validator.dict()
    except Exception as e:
        raise ValueError(f"Search query validation failed: {e}")


def batch_validate_regulations(regulations: List[Dict[str, Any]]) -> BatchValidationResult:
    """
    Validate a batch of regulation data
    
    Args:
        regulations: List of regulation data dictionaries
        
    Returns:
        Batch validation result
    """
    total_items = len(regulations)
    valid_items = 0
    errors = []
    warnings = []
    
    for i, regulation in enumerate(regulations):
        try:
            validate_regulation_data(regulation)
            valid_items += 1
        except ValueError as e:
            errors.append({
                "index": i,
                "error": str(e),
                "data_preview": str(regulation)[:100] + "..." if len(str(regulation)) > 100 else str(regulation)
            })
    
    success_rate = valid_items / total_items if total_items > 0 else 0.0
    
    return BatchValidationResult(
        total_items=total_items,
        valid_items=valid_items,
        invalid_items=total_items - valid_items,
        errors=errors,
        warnings=warnings,
        success_rate=success_rate
    )