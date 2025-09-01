"""
Learning Models for Jurisdiction Knowledge Base
Stores learned patterns, extraction strategies, and reinforcement data
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json


class ExtractionConfidence(str, Enum):
    """Confidence levels for extraction patterns"""
    VERY_HIGH = "very_high"  # 0.9+
    HIGH = "high"           # 0.7-0.9
    MEDIUM = "medium"       # 0.5-0.7
    LOW = "low"            # 0.3-0.5
    VERY_LOW = "very_low"   # <0.3


class PatternType(str, Enum):
    """Types of extraction patterns"""
    CSS_SELECTOR = "css_selector"
    XPATH = "xpath"
    URL_PATTERN = "url_pattern"
    DATE_FORMAT = "date_format"
    CONTENT_REGEX = "content_regex"
    PAGE_STRUCTURE = "page_structure"


@dataclass
class ExtractionPattern:
    """A learned pattern for extracting content from a specific source"""
    pattern_id: str
    pattern_type: PatternType
    pattern_value: str
    description: str
    
    # Learning metrics
    success_count: int = 0
    failure_count: int = 0
    confidence_score: float = 0.5
    last_used: Optional[datetime] = None
    last_successful: Optional[datetime] = None
    
    # Context
    applies_to: List[str] = field(default_factory=list)  # URLs, source_ids, etc.
    created_date: datetime = field(default_factory=datetime.utcnow)
    
    # Performance metrics
    avg_extraction_time: float = 0.0
    avg_items_found: float = 0.0
    
    def update_success(self, items_found: int = 0, extraction_time: float = 0.0):
        """Update pattern after successful use"""
        self.success_count += 1
        self.last_used = datetime.utcnow()
        self.last_successful = datetime.utcnow()
        
        # Update confidence (reinforcement learning)
        total_attempts = self.success_count + self.failure_count
        self.confidence_score = self.success_count / total_attempts
        
        # Update performance metrics
        if items_found > 0:
            self.avg_items_found = (self.avg_items_found * (self.success_count - 1) + items_found) / self.success_count
        
        if extraction_time > 0:
            self.avg_extraction_time = (self.avg_extraction_time * (self.success_count - 1) + extraction_time) / self.success_count
    
    def update_failure(self, error_type: str = ""):
        """Update pattern after failed use"""
        self.failure_count += 1
        self.last_used = datetime.utcnow()
        
        # Update confidence (reinforcement learning)
        total_attempts = self.success_count + self.failure_count
        self.confidence_score = self.success_count / total_attempts
    
    def get_confidence_level(self) -> ExtractionConfidence:
        """Get categorical confidence level"""
        if self.confidence_score >= 0.9:
            return ExtractionConfidence.VERY_HIGH
        elif self.confidence_score >= 0.7:
            return ExtractionConfidence.HIGH
        elif self.confidence_score >= 0.5:
            return ExtractionConfidence.MEDIUM
        elif self.confidence_score >= 0.3:
            return ExtractionConfidence.LOW
        else:
            return ExtractionConfidence.VERY_LOW


@dataclass 
class SourceProfile:
    """Learned profile for a specific regulatory source"""
    source_id: str
    source_name: str
    base_url: str
    jurisdiction: str
    
    # Learned extraction patterns
    extraction_patterns: Dict[str, ExtractionPattern] = field(default_factory=dict)
    
    # Page structure intelligence
    daily_publication_paths: List[str] = field(default_factory=list)
    date_formats: List[str] = field(default_factory=list)
    content_indicators: List[str] = field(default_factory=list)
    
    # Timing patterns
    typical_update_times: List[str] = field(default_factory=list)  # ["08:00 CET", "14:00 CET"]
    last_update_detected: Optional[datetime] = None
    
    # Performance metrics
    overall_success_rate: float = 0.5
    avg_items_per_session: float = 0.0
    avg_extraction_time: float = 0.0
    
    # Learning metadata
    first_learned: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    learning_sessions: int = 0
    
    def add_pattern(self, pattern: ExtractionPattern):
        """Add a new learned pattern"""
        self.extraction_patterns[pattern.pattern_id] = pattern
        self.last_updated = datetime.utcnow()
    
    def get_best_patterns(self, pattern_type: PatternType, min_confidence: float = 0.5) -> List[ExtractionPattern]:
        """Get best patterns of a specific type"""
        patterns = [
            p for p in self.extraction_patterns.values()
            if p.pattern_type == pattern_type and p.confidence_score >= min_confidence
        ]
        return sorted(patterns, key=lambda x: x.confidence_score, reverse=True)
    
    def update_success_metrics(self, items_found: int, extraction_time: float):
        """Update overall success metrics"""
        self.learning_sessions += 1
        self.avg_items_per_session = (self.avg_items_per_session * (self.learning_sessions - 1) + items_found) / self.learning_sessions
        self.avg_extraction_time = (self.avg_extraction_time * (self.learning_sessions - 1) + extraction_time) / self.learning_sessions
        self.last_updated = datetime.utcnow()


@dataclass
class JurisdictionProfile:
    """Learned profile for an entire jurisdiction"""
    jurisdiction_name: str
    jurisdiction_code: str  # ES, DE, US, etc.
    
    # Source profiles in this jurisdiction
    source_profiles: Dict[str, SourceProfile] = field(default_factory=dict)
    
    # Common patterns across jurisdiction
    common_date_formats: List[str] = field(default_factory=list)
    common_content_patterns: List[str] = field(default_factory=list)
    common_page_structures: List[str] = field(default_factory=list)
    
    # Language and locale information
    primary_language: str = ""
    locale_info: Dict[str, str] = field(default_factory=dict)
    
    # Jurisdiction-wide metrics
    total_sources: int = 0
    avg_success_rate: float = 0.5
    total_learning_sessions: int = 0
    
    # Learning metadata
    first_discovered: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def add_source_profile(self, profile: SourceProfile):
        """Add a source profile to this jurisdiction"""
        self.source_profiles[profile.source_id] = profile
        self.total_sources = len(self.source_profiles)
        self.last_updated = datetime.utcnow()
    
    def get_common_patterns(self, pattern_type: PatternType, min_sources: int = 2) -> List[str]:
        """Get patterns common across multiple sources in this jurisdiction"""
        pattern_counts = {}
        
        for source in self.source_profiles.values():
            for pattern in source.extraction_patterns.values():
                if pattern.pattern_type == pattern_type:
                    pattern_counts[pattern.pattern_value] = pattern_counts.get(pattern.pattern_value, 0) + 1
        
        return [pattern for pattern, count in pattern_counts.items() if count >= min_sources]


@dataclass 
class LearningSession:
    """Record of a learning/extraction session"""
    session_id: str
    timestamp: datetime
    source_id: str
    jurisdiction: str
    
    # What was attempted
    extraction_method: str
    patterns_used: List[str] = field(default_factory=list)
    
    # Results
    success: bool = False
    items_found: int = 0
    extraction_time: float = 0.0
    error_message: Optional[str] = None
    
    # Learning outcomes
    new_patterns_discovered: List[str] = field(default_factory=list)
    patterns_reinforced: List[str] = field(default_factory=list)
    patterns_weakened: List[str] = field(default_factory=list)
    
    # Feedback for future learning
    notes: List[str] = field(default_factory=list)


class JurisdictionKnowledgeBase:
    """Central knowledge base for all learned jurisdiction patterns"""
    
    def __init__(self, storage_path: str):
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Storage files
        self.jurisdictions_file = self.storage_path / "jurisdiction_profiles.json"
        self.learning_sessions_file = self.storage_path / "learning_sessions.json"
        
        # In-memory data
        self.jurisdiction_profiles: Dict[str, JurisdictionProfile] = {}
        self.learning_sessions: List[LearningSession] = []
        
        # Load existing data
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load existing knowledge base from storage"""
        try:
            if self.jurisdictions_file.exists():
                with open(self.jurisdictions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for jurisdiction_code, jurisdiction_data in data.items():
                    profile = JurisdictionProfile(**jurisdiction_data)
                    # Convert source profiles
                    for source_id, source_data in jurisdiction_data.get('source_profiles', {}).items():
                        source_profile = SourceProfile(**source_data)
                        # Convert extraction patterns
                        for pattern_id, pattern_data in source_data.get('extraction_patterns', {}).items():
                            pattern = ExtractionPattern(**pattern_data)
                            source_profile.extraction_patterns[pattern_id] = pattern
                        profile.source_profiles[source_id] = source_profile
                    self.jurisdiction_profiles[jurisdiction_code] = profile
            
            if self.learning_sessions_file.exists():
                with open(self.learning_sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    self.learning_sessions = [LearningSession(**session) for session in sessions_data]
                    
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
    
    def save_knowledge_base(self):
        """Save knowledge base to storage"""
        try:
            # Save jurisdiction profiles
            jurisdictions_data = {}
            for code, profile in self.jurisdiction_profiles.items():
                profile_dict = asdict(profile)
                # Convert datetime objects to strings
                if isinstance(profile.first_discovered, datetime):
                    profile_dict['first_discovered'] = profile.first_discovered.isoformat()
                elif isinstance(profile.first_discovered, str):
                    profile_dict['first_discovered'] = profile.first_discovered
                else:
                    profile_dict['first_discovered'] = datetime.utcnow().isoformat()
                    
                if isinstance(profile.last_updated, datetime):
                    profile_dict['last_updated'] = profile.last_updated.isoformat()
                elif isinstance(profile.last_updated, str):
                    profile_dict['last_updated'] = profile.last_updated
                else:
                    profile_dict['last_updated'] = datetime.utcnow().isoformat()
                
                # Convert source profiles
                for source_id, source_profile in profile_dict['source_profiles'].items():
                    # Handle datetime conversion safely
                    if isinstance(source_profile.get('first_learned'), datetime):
                        source_profile['first_learned'] = source_profile['first_learned'].isoformat()
                    elif not source_profile.get('first_learned'):
                        source_profile['first_learned'] = datetime.utcnow().isoformat()
                    
                    if isinstance(source_profile.get('last_updated'), datetime):
                        source_profile['last_updated'] = source_profile['last_updated'].isoformat() 
                    elif not source_profile.get('last_updated'):
                        source_profile['last_updated'] = datetime.utcnow().isoformat()
                    
                    # Convert extraction patterns
                    for pattern_id, pattern in source_profile['extraction_patterns'].items():
                        if isinstance(pattern.get('created_date'), datetime):
                            pattern['created_date'] = pattern['created_date'].isoformat()
                        elif not pattern.get('created_date'):
                            pattern['created_date'] = datetime.utcnow().isoformat()
                            
                        if isinstance(pattern.get('last_used'), datetime):
                            pattern['last_used'] = pattern['last_used'].isoformat()
                        elif pattern.get('last_used') is None:
                            pattern['last_used'] = None
                            
                        if isinstance(pattern.get('last_successful'), datetime):
                            pattern['last_successful'] = pattern['last_successful'].isoformat()
                        elif pattern.get('last_successful') is None:
                            pattern['last_successful'] = None
                
                jurisdictions_data[code] = profile_dict
            
            with open(self.jurisdictions_file, 'w', encoding='utf-8') as f:
                json.dump(jurisdictions_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Save learning sessions
            sessions_data = []
            for session in self.learning_sessions:
                session_dict = asdict(session)
                # Handle timestamp conversion safely
                if isinstance(session.timestamp, datetime):
                    session_dict['timestamp'] = session.timestamp.isoformat()
                elif isinstance(session.timestamp, str):
                    session_dict['timestamp'] = session.timestamp
                else:
                    session_dict['timestamp'] = datetime.utcnow().isoformat()
                sessions_data.append(session_dict)
            
            with open(self.learning_sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving knowledge base: {e}")
    
    def get_or_create_jurisdiction(self, jurisdiction_code: str, jurisdiction_name: str = "") -> JurisdictionProfile:
        """Get existing or create new jurisdiction profile"""
        if jurisdiction_code not in self.jurisdiction_profiles:
            self.jurisdiction_profiles[jurisdiction_code] = JurisdictionProfile(
                jurisdiction_name=jurisdiction_name or jurisdiction_code,
                jurisdiction_code=jurisdiction_code
            )
            self.save_knowledge_base()
        
        return self.jurisdiction_profiles[jurisdiction_code]
    
    def get_or_create_source_profile(self, source_id: str, source_name: str, base_url: str, jurisdiction: str) -> SourceProfile:
        """Get existing or create new source profile"""
        jurisdiction_profile = self.get_or_create_jurisdiction(jurisdiction)
        
        if source_id not in jurisdiction_profile.source_profiles:
            source_profile = SourceProfile(
                source_id=source_id,
                source_name=source_name,
                base_url=base_url,
                jurisdiction=jurisdiction
            )
            jurisdiction_profile.add_source_profile(source_profile)
            self.save_knowledge_base()
        
        return jurisdiction_profile.source_profiles[source_id]
    
    def record_learning_session(self, session: LearningSession):
        """Record a learning session for analysis"""
        self.learning_sessions.append(session)
        self.save_knowledge_base()
    
    def get_recommended_patterns(self, source_id: str, pattern_type: PatternType, min_confidence: float = 0.7) -> List[ExtractionPattern]:
        """Get recommended patterns for a source based on learning"""
        # First try source-specific patterns
        for jurisdiction in self.jurisdiction_profiles.values():
            if source_id in jurisdiction.source_profiles:
                source_patterns = jurisdiction.source_profiles[source_id].get_best_patterns(pattern_type, min_confidence)
                if source_patterns:
                    return source_patterns
        
        # Fall back to jurisdiction-wide patterns
        # This is where we could implement transfer learning between similar sources
        return []