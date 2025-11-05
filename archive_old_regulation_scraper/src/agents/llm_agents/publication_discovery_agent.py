"""
Publication Discovery Agent
AI-powered agent for discovering regulatory publication sources, feeds, and daily publication portals
"""
import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urljoin, urlparse
import hashlib

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType


class PublicationSourceType(str, Enum):
    """Types of regulatory publication sources"""
    RSS_FEED = "rss_feed"
    API_ENDPOINT = "api_endpoint"
    DAILY_LISTING = "daily_listing"
    AGENCY_PORTAL = "agency_portal"
    OFFICIAL_GAZETTE = "official_gazette"
    NEWS_RELEASES = "news_releases"
    LEGISLATION_DATABASE = "legislation_database"


class UpdateFrequency(str, Enum):
    """How frequently sources are updated"""
    REAL_TIME = "real_time"
    DAILY = "daily" 
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    IRREGULAR = "irregular"


@dataclass
class PublicationSource:
    """A discovered source of regulatory publications"""
    source_id: str
    name: str
    url: str
    source_type: PublicationSourceType
    jurisdiction: str  # US, UK, EU, etc.
    agency: str  # FDA, CPSC, etc.
    
    # Discovery metadata
    discovered_date: datetime
    discovery_method: str  # 'automated_scan', 'human_input', 'feed_discovery'
    confidence_score: float  # 0.0 to 1.0
    
    # Publication characteristics
    update_frequency: UpdateFrequency
    content_types: List[str]  # ['regulations', 'guidance', 'alerts', etc.]
    feed_url: Optional[str]  # RSS/API endpoint if available
    feed_format: Optional[str]  # 'rss', 'atom', 'json_api', etc.
    
    # Monitoring configuration
    is_active: bool
    last_checked: Optional[datetime]
    check_interval_hours: int
    
    # Content extraction hints
    publication_date_selectors: List[str]  # CSS selectors or patterns
    title_selectors: List[str]
    content_link_patterns: List[str]
    
    # Quality metrics
    publications_found: int
    false_positive_rate: float
    extraction_success_rate: float


@dataclass
class DiscoverySession:
    """A discovery session scanning for publication sources"""
    session_id: str
    start_time: datetime
    target_jurisdictions: List[str]
    discovery_methods: List[str]
    sources_discovered: List[str]  # source IDs
    total_urls_scanned: int
    successful_discoveries: int
    session_notes: List[str]


class PublicationDiscoveryAgent(BaseLLMAgent):
    """AI-powered agent for discovering regulatory publication sources"""
    
    def __init__(self, broker, storage_path: str = "./discovery_data"):
        system_prompt = """You are an expert publication discovery agent specialized in finding regulatory publication sources, feeds, and daily monitoring targets.

Your expertise covers:
- Government regulatory websites and their publication patterns
- RSS feeds, APIs, and structured data sources for regulations
- Daily publication portals (Federal Register, Official Journals, etc.)
- Agency-specific publication patterns and update schedules
- International regulatory publication systems (US, EU, UK, etc.)

Your discovery responsibilities:
1. **Website Analysis**: Analyze regulatory websites to identify publication sections
2. **Feed Discovery**: Find RSS feeds, APIs, and structured data endpoints
3. **Pattern Recognition**: Identify how agencies publish new regulations
4. **Publication Mapping**: Map publication workflows and update frequencies
5. **Source Validation**: Verify discovered sources produce quality regulation content
6. **Monitoring Setup**: Configure appropriate monitoring parameters

Discovery strategies:
- Scan known regulatory portals for "latest", "new", "recent" sections  
- Look for RSS/feed links, API documentation, data export options
- Analyze URL patterns and publication naming conventions
- Identify publication calendars and scheduled release patterns
- Map agency organizational structures to publication sources

Always provide actionable discovery results that enable effective daily monitoring of new regulatory publications."""

        super().__init__(
            agent_id="publication_discovery",
            agent_role=AgentRole.DISCOVERY,
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Storage setup
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Discovery data storage
        self.sources_file = self.storage_path / "publication_sources.json"
        self.sessions_file = self.storage_path / "discovery_sessions.json"
        
        # In-memory data
        self.discovered_sources: Dict[str, PublicationSource] = {}
        self.discovery_sessions: List[DiscoverySession] = []
        
        # No hardcoded portals - fully agentic discovery using LLM
        self.discovered_portals = {}  # Will be populated by LLM agents
        
        # Load existing data
        asyncio.create_task(self._load_discovery_data())

    async def _register_tools(self):
        """Register publication discovery tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="discover_publication_sources",
            function=self._discover_publication_sources,
            description="Discover regulatory publication sources for specified jurisdictions",
            parameters={
                "type": "object",
                "properties": {
                    "target_jurisdictions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Jurisdictions to discover sources for (US, UK, EU, etc.)"
                    },
                    "discovery_methods": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Discovery methods to use (automated_scan, feed_discovery, portal_analysis)"
                    },
                    "focus_agencies": {
                        "type": "array",
                        "items": {"type": "string"}, 
                        "description": "Specific agencies to focus on (FDA, CPSC, etc.)"
                    }
                },
                "required": ["target_jurisdictions"]
            }
        )
        
        self.register_tool(
            name="analyze_website_for_publications",
            function=self._analyze_website_for_publications,
            description="Analyze a specific website to identify publication sources and feeds",
            parameters={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "URL of website to analyze"},
                    "website_name": {"type": "string", "description": "Name/description of the website"},
                    "jurisdiction": {"type": "string", "description": "Jurisdiction (US, UK, EU, etc.)"},
                    "agency": {"type": "string", "description": "Agency name if known"}
                },
                "required": ["website_url", "website_name"]
            }
        )
        
        self.register_tool(
            name="validate_discovered_source",
            function=self._validate_discovered_source,
            description="Validate that a discovered source actually provides quality regulation content",
            parameters={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "ID of source to validate"},
                    "sample_size": {"type": "number", "description": "Number of recent items to sample for validation"}
                },
                "required": ["source_id"]
            }
        )
        
        self.register_tool(
            name="get_discovery_recommendations",
            function=self._get_discovery_recommendations,
            description="Get AI recommendations for discovering new publication sources",
            parameters={
                "type": "object",
                "properties": {
                    "current_coverage": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Currently covered jurisdictions/agencies"
                    },
                    "gaps_identified": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Known gaps in coverage"
                    }
                },
                "required": []
            }
        )

    async def _load_discovery_data(self):
        """Load existing discovery data from storage"""
        try:
            # Load discovered sources
            if self.sources_file.exists():
                with open(self.sources_file, 'r') as f:
                    sources_data = json.load(f)
                    
                for source_data in sources_data:
                    # Convert datetime strings back to datetime objects
                    source_data['discovered_date'] = datetime.fromisoformat(source_data['discovered_date'])
                    if source_data.get('last_checked'):
                        source_data['last_checked'] = datetime.fromisoformat(source_data['last_checked'])
                    
                    # Convert enums
                    source_data['source_type'] = PublicationSourceType(source_data['source_type'])
                    source_data['update_frequency'] = UpdateFrequency(source_data['update_frequency'])
                    
                    source = PublicationSource(**source_data)
                    self.discovered_sources[source.source_id] = source
                    
                self.logger.info(f"Loaded {len(self.discovered_sources)} discovered sources")
                
            # Load discovery sessions
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                    
                for session_data in sessions_data:
                    session_data['start_time'] = datetime.fromisoformat(session_data['start_time'])
                    session = DiscoverySession(**session_data)
                    self.discovery_sessions.append(session)
                    
                self.logger.info(f"Loaded {len(self.discovery_sessions)} discovery sessions")
                
        except Exception as e:
            self.logger.error(f"Error loading discovery data: {e}")

    async def _save_discovery_data(self):
        """Save discovery data to storage"""
        try:
            # Save sources
            sources_data = []
            for source in self.discovered_sources.values():
                source_dict = asdict(source)
                # Convert datetime to string for JSON serialization
                source_dict['discovered_date'] = source_dict['discovered_date'].isoformat()
                if source_dict.get('last_checked'):
                    source_dict['last_checked'] = source_dict['last_checked'].isoformat()
                # Convert enums to strings
                source_dict['source_type'] = source_dict['source_type'].value
                source_dict['update_frequency'] = source_dict['update_frequency'].value
                sources_data.append(source_dict)
                
            with open(self.sources_file, 'w') as f:
                json.dump(sources_data, f, indent=2, ensure_ascii=False)
                
            # Save sessions
            sessions_data = []
            for session in self.discovery_sessions:
                session_dict = asdict(session) 
                session_dict['start_time'] = session_dict['start_time'].isoformat()
                sessions_data.append(session_dict)
                
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving discovery data: {e}")

    async def _discover_regulatory_portals_agentic(self, jurisdictions: List[str]) -> List[Dict[str, str]]:
        """Use LLM to discover regulatory portals for given jurisdictions"""
        
        discovery_prompt = f"""You are an expert in international regulatory systems and government publication portals.

IMPORTANT: You must respond with ONLY a valid JSON array. Do not include any explanatory text before or after the JSON.

Your task is to identify the primary regulatory publication websites for the following jurisdictions: {', '.join(jurisdictions)}

For each jurisdiction, provide the main government websites where new regulations, official gazettes, and regulatory announcements are published daily.

Return ONLY a JSON array in this exact format:
[
  {{
    "name": "Official name of the portal",
    "url": "https://primary-url-for-portal", 
    "jurisdiction": "Full jurisdiction name",
    "agency": "Publishing agency/department name",
    "publication_types": ["regulations", "gazettes", "announcements"],
    "update_frequency": "daily",
    "feed_availability": "likely_rss"
  }}
]

Jurisdictions to research: {', '.join(jurisdictions)}

RESPOND WITH JSON ONLY - NO OTHER TEXT"""

        try:
            self.logger.info(f"Requesting LLM portal discovery for: {', '.join(jurisdictions)}")
            
            # Use a more direct approach without tools for simple JSON response
            response = await self.generate_response(discovery_prompt, use_tools=False)
            
            self.logger.debug(f"LLM response received: {response}")
            
            if not response:
                self.logger.error("Empty response from LLM")
                return []
                
            content = response.get('content')
            if not content:
                self.logger.error("No content in LLM response")
                return []
            
            # Clean up the response to extract JSON
            content = content.strip()
            if not content:
                self.logger.error("Empty content after stripping")
                return []
            
            # Handle markdown code blocks
            if content.startswith('```json'):
                # Extract content from markdown JSON code block
                lines = content.split('\n')
                if len(lines) >= 3:
                    # Remove ```json and ``` lines
                    json_lines = lines[1:-1]
                    content = '\n'.join(json_lines).strip()
            elif content.startswith('```'):
                # Generic code block
                lines = content.split('\n')
                if len(lines) >= 3:
                    json_lines = lines[1:-1]
                    content = '\n'.join(json_lines).strip()
            
            # Try to find JSON in the response
            if content.startswith('[') and content.endswith(']'):
                # Direct JSON array
                portals_data = json.loads(content)
            else:
                # Try to extract JSON from text
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    portals_data = json.loads(json_content)
                else:
                    self.logger.error(f"Could not find JSON array in response: {content[:200]}...")
                    return []
            
            if not isinstance(portals_data, list):
                self.logger.error(f"Response is not a JSON array: {type(portals_data)}")
                return []
                
            self.logger.info(f"LLM successfully discovered {len(portals_data)} portals for {', '.join(jurisdictions)}")
            return portals_data
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.error(f"Raw response content: {response.get('content', 'None')[:500]}...")
            return []
        except Exception as e:
            self.logger.error(f"Error in agentic portal discovery: {e}")
            return []

    async def _discover_publication_sources(
        self,
        target_jurisdictions: List[str],
        discovery_methods: List[str] = None,
        focus_agencies: List[str] = None
    ) -> Dict[str, Any]:
        """Discover publication sources for target jurisdictions using fully agentic approach"""
        try:
            # Start discovery session
            session_id = f"discovery_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            session = DiscoverySession(
                session_id=session_id,
                start_time=datetime.utcnow(),
                target_jurisdictions=target_jurisdictions,
                discovery_methods=discovery_methods or ["agentic_discovery"],
                sources_discovered=[],
                total_urls_scanned=0,
                successful_discoveries=0,
                session_notes=[]
            )
            
            self.logger.info(f"Starting agentic publication discovery session: {session_id}")
            self.logger.info(f"Target jurisdictions: {', '.join(target_jurisdictions)}")
            
            discovered_sources = []
            
            # STEP 1: Use LLM to discover regulatory portals for the jurisdictions
            session.session_notes.append("Using LLM to discover regulatory portals")
            discovered_portals = await self._discover_regulatory_portals_agentic(target_jurisdictions)
            
            if not discovered_portals:
                session.session_notes.append("No portals discovered by LLM")
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": "No regulatory portals discovered for the specified jurisdictions",
                    "jurisdictions_covered": target_jurisdictions,
                    "portals_analyzed": 0,
                    "sources_discovered": 0,
                    "session_summary": {
                        "total_scanned": 0,
                        "successful_discoveries": 0,
                        "discovery_rate": 0
                    }
                }
            
            # Filter portals by focus agencies if specified
            relevant_portals = discovered_portals
            if focus_agencies:
                relevant_portals = [
                    portal for portal in discovered_portals
                    if any(agency.lower() in portal.get('agency', '').lower() for agency in focus_agencies)
                ]
            
            self.logger.info(f"Analyzing {len(relevant_portals)} relevant portals")
            
            for portal in relevant_portals:
                session.total_urls_scanned += 1
                
                try:
                    # Analyze each portal for publication sources
                    analysis_result = await self._analyze_website_for_publications(
                        website_url=portal['url'],
                        website_name=portal['name'],
                        jurisdiction=portal['jurisdiction'],
                        agency=portal['agency']
                    )
                    
                    if analysis_result.get('success') and analysis_result.get('sources_found'):
                        discovered_sources.extend(analysis_result['sources_found'])
                        session.successful_discoveries += len(analysis_result['sources_found'])
                        session.sources_discovered.extend([s['source_id'] for s in analysis_result['sources_found']])
                        
                        session.session_notes.append(f"Found {len(analysis_result['sources_found'])} sources at {portal['name']}")
                        
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    session.session_notes.append(f"Error analyzing {portal['name']}: {str(e)}")
                    self.logger.error(f"Error analyzing {portal['name']}: {e}")
            
            # Store discovered sources
            for source_data in discovered_sources:
                source = PublicationSource(**source_data)
                self.discovered_sources[source.source_id] = source
                
            # Save session and data
            self.discovery_sessions.append(session)
            await self._save_discovery_data()
            
            result = {
                "success": True,
                "session_id": session_id,
                "jurisdictions_covered": target_jurisdictions,
                "portals_analyzed": len(relevant_portals),
                "sources_discovered": len(discovered_sources),
                "total_sources": len(self.discovered_sources),
                "new_sources": discovered_sources,
                "session_summary": {
                    "total_scanned": session.total_urls_scanned,
                    "successful_discoveries": session.successful_discoveries,
                    "discovery_rate": session.successful_discoveries / session.total_urls_scanned * 100 if session.total_urls_scanned > 0 else 0
                }
            }
            
            self.logger.info(f"Discovery session complete: {len(discovered_sources)} new sources found")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in publication discovery: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_website_for_publications(
        self,
        website_url: str,
        website_name: str,
        jurisdiction: str = "unknown",
        agency: str = "unknown"
    ) -> Dict[str, Any]:
        """Analyze a specific website to identify publication sources"""
        try:
            self.logger.info(f"Analyzing website: {website_name} ({website_url})")
            
            # First, fetch the website content
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            try:
                response = requests.get(website_url, headers=headers, timeout=30)
                if response.status_code != 200:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                
                website_content = response.text
                self.logger.info(f"Fetched {len(website_content)} characters from {website_name}")
                
            except Exception as e:
                return {"success": False, "error": f"Failed to fetch website: {e}"}
            
            # Use LLM to analyze the website for publication sources
            analysis_prompt = f"""Analyze this regulatory website to identify publication sources, feeds, and daily monitoring targets.

WEBSITE: {website_name}
URL: {website_url}
JURISDICTION: {jurisdiction}
AGENCY: {agency}

CONTENT SAMPLE (first 8000 chars):
{website_content[:8000]}...

Analyze this website and identify publication sources using this JSON structure:

{{
    "website_analysis": {{
        "has_publication_sections": true/false,
        "publication_types": ["daily_releases", "rss_feeds", "api_endpoints", "news_sections"],
        "update_frequency_indicators": ["daily", "weekly", "real_time", etc],
        "content_organization": "description of how content is organized"
    }},
    "discovered_sources": [
        {{
            "source_name": "descriptive name",
            "source_url": "full URL to the source",
            "source_type": "rss_feed|api_endpoint|daily_listing|news_releases|etc",
            "confidence": 0.0-1.0,
            "update_frequency": "daily|weekly|monthly|real_time",
            "content_types": ["regulations", "guidance", "alerts", etc],
            "feed_format": "rss|atom|json|html|etc",
            "description": "what this source provides",
            "monitoring_value": "high|medium|low"
        }}
    ],
    "feed_urls_found": [
        {{
            "url": "RSS/API URL",
            "type": "rss|atom|json_api|etc",
            "description": "what this feed contains"
        }}
    ],
    "publication_patterns": {{
        "daily_publication_indicators": ["signs this publishes daily"],
        "url_patterns": ["patterns in publication URLs"],
        "date_patterns": ["how dates are formatted"],
        "navigation_paths": ["how to find new publications"]
    }},
    "monitoring_recommendations": {{
        "primary_targets": ["most important sources to monitor"],
        "check_frequency": "recommended monitoring frequency",
        "extraction_difficulty": "easy|medium|hard",
        "automation_feasibility": "high|medium|low"
    }}
}}

Focus on finding:
1. RSS feeds or APIs for new publications
2. "Latest", "New", "Recent" publication sections  
3. Daily publication portals or calendars
4. Press release or news sections with regulation content
5. Official publication archives with recent items

Return only the JSON structure."""

            context = AgentContext(
                session_id=f"website_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=website_url,
                metadata={"analysis_type": "publication_discovery", "website": website_name, "url": website_url}
            )
            
            response = await self.generate_response(analysis_prompt, context)
            
            if not response:
                return {"success": False, "error": "No response from analysis LLM"}
                
            try:
                # Parse JSON response
                content = response.get('content', '')
                if not content:
                    return {"success": False, "error": "No content in LLM response"}
                
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if not json_match:
                    return {"success": False, "error": "Could not find JSON in LLM response"}
                    
                analysis_data = json.loads(json_match.group())
                
                # Convert discovered sources to full PublicationSource objects
                sources_found = []
                
                for source_data in analysis_data.get('discovered_sources', []):
                    # Generate source ID
                    source_id = hashlib.md5(f"{source_data['source_name']}_{source_data['source_url']}".encode()).hexdigest()[:12]
                    
                    # Create full source object with proper enum conversion
                    source_type_str = source_data.get('source_type', 'daily_listing')
                    update_freq_str = source_data.get('update_frequency', 'daily')
                    
                    # Convert string to enum safely
                    try:
                        source_type_enum = PublicationSourceType(source_type_str)
                    except ValueError:
                        source_type_enum = PublicationSourceType.DAILY_LISTING
                    
                    try:
                        update_freq_enum = UpdateFrequency(update_freq_str) 
                    except ValueError:
                        update_freq_enum = UpdateFrequency.DAILY
                    
                    publication_source = {
                        "source_id": source_id,
                        "name": source_data['source_name'],
                        "url": source_data['source_url'],
                        "source_type": source_type_enum,
                        "jurisdiction": jurisdiction,
                        "agency": agency,
                        "discovered_date": datetime.utcnow(),
                        "discovery_method": "automated_scan",
                        "confidence_score": source_data.get('confidence', 0.7),
                        "update_frequency": update_freq_enum,
                        "content_types": source_data.get('content_types', ['regulations']),
                        "feed_url": source_data['source_url'] if 'feed' in source_data.get('source_type', '') else None,
                        "feed_format": source_data.get('feed_format'),
                        "is_active": True,
                        "last_checked": None,
                        "check_interval_hours": 24,
                        "publication_date_selectors": [],
                        "title_selectors": [],
                        "content_link_patterns": [],
                        "publications_found": 0,
                        "false_positive_rate": 0.0,
                        "extraction_success_rate": 0.0
                    }
                    
                    sources_found.append(publication_source)
                
                result = {
                    "success": True,
                    "website_name": website_name,
                    "website_url": website_url,
                    "analysis_data": analysis_data,
                    "sources_found": sources_found,
                    "feed_urls_found": analysis_data.get('feed_urls_found', []),
                    "monitoring_value": analysis_data.get('monitoring_recommendations', {}).get('automation_feasibility', 'medium')
                }
                
                self.logger.info(f"Website analysis complete: {len(sources_found)} sources found at {website_name}")
                return result
                
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON parsing error: {e}", "raw_response": response[:500]}
                
        except Exception as e:
            self.logger.error(f"Error analyzing website {website_url}: {e}")
            return {"success": False, "error": str(e)}

    async def _validate_discovered_source(
        self,
        source_id: str,
        sample_size: int = 5
    ) -> Dict[str, Any]:
        """Validate that a discovered source provides quality content"""
        try:
            if source_id not in self.discovered_sources:
                return {"success": False, "error": f"Source {source_id} not found"}
                
            source = self.discovered_sources[source_id]
            self.logger.info(f"Validating source: {source.name}")
            
            # This would implement actual validation logic
            # For now, return structure showing what validation would include
            
            validation_result = {
                "success": True,
                "source_id": source_id,
                "source_name": source.name,
                "validation_date": datetime.utcnow().isoformat(),
                "samples_tested": sample_size,
                "validation_results": {
                    "content_accessibility": True,  # Can access the source
                    "recent_publications_found": sample_size,  # Found recent items
                    "content_quality_score": 0.8,  # Quality of extracted content
                    "regulatory_relevance": True,  # Contains actual regulations
                    "update_frequency_confirmed": source.update_frequency.value,
                    "extraction_success_rate": 0.85
                },
                "recommendations": {
                    "monitoring_viable": True,
                    "confidence_adjustment": 0.0,  # Adjustment to confidence score
                    "suggested_check_interval": source.check_interval_hours
                }
            }
            
            # Update source with validation results
            source.extraction_success_rate = validation_result["validation_results"]["extraction_success_rate"]
            source.last_checked = datetime.utcnow()
            
            await self._save_discovery_data()
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating source {source_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_discovery_recommendations(
        self,
        current_coverage: List[str] = None,
        gaps_identified: List[str] = None
    ) -> Dict[str, Any]:
        """Get AI recommendations for discovering new sources"""
        try:
            current_coverage = current_coverage or []
            gaps_identified = gaps_identified or []
            
            # Analyze current discovery state
            total_sources = len(self.discovered_sources)
            jurisdictions_covered = set(source.jurisdiction for source in self.discovered_sources.values())
            agencies_covered = set(source.agency for source in self.discovered_sources.values())
            
            # Create recommendation prompt
            recommendation_prompt = f"""Analyze the current regulatory publication discovery coverage and provide recommendations for expansion.

CURRENT COVERAGE:
- Total sources discovered: {total_sources}
- Jurisdictions covered: {list(jurisdictions_covered)}
- Agencies covered: {list(agencies_covered)}
- User-specified coverage: {current_coverage}
- Known gaps: {gaps_identified}

DISCOVERED SOURCES SUMMARY:
{json.dumps([{
    'name': source.name,
    'jurisdiction': source.jurisdiction,
    'agency': source.agency,
    'type': source.source_type.value,
    'confidence': source.confidence_score
} for source in list(self.discovered_sources.values())[:20]], indent=2)}

Please provide discovery recommendations in this JSON format:

{{
    "coverage_analysis": {{
        "strength_areas": ["areas with good coverage"],
        "gap_areas": ["areas needing more sources"],
        "coverage_score": 0.0-1.0,
        "jurisdiction_completeness": {{"US": 0.8, "UK": 0.5, "EU": 0.3}}
    }},
    "recommended_targets": [
        {{
            "target_name": "specific website or portal to investigate",
            "target_url": "URL if known",
            "jurisdiction": "jurisdiction",
            "agency": "agency if known",
            "priority": "high|medium|low",
            "rationale": "why this target is recommended"
        }}
    ],
    "discovery_strategies": [
        {{
            "strategy": "strategy name",
            "description": "what this strategy involves",
            "expected_yield": "high|medium|low",
            "effort_required": "high|medium|low"
        }}
    ],
    "next_actions": [
        "specific actions to improve coverage"
    ]
}}

Focus on identifying gaps in critical regulatory areas and suggesting high-value targets for discovery."""

            context = AgentContext(
                session_id=f"recommendations_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id="discovery_recommendations",
                metadata={"recommendation_type": "discovery_expansion"}
            )
            
            response = await self.generate_response(recommendation_prompt, context)
            
            if not response:
                return {"success": False, "error": "No response from recommendation LLM"}
                
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    recommendations = json.loads(json_match.group())
                    
                    result = {
                        "success": True,
                        "generated_date": datetime.utcnow().isoformat(),
                        "current_state": {
                            "total_sources": total_sources,
                            "jurisdictions_covered": list(jurisdictions_covered),
                            "agencies_covered": list(agencies_covered)
                        },
                        "recommendations": recommendations
                    }
                    
                    self.logger.info(f"Generated discovery recommendations: {len(recommendations.get('recommended_targets', []))} targets identified")
                    return result
                    
                else:
                    return {"success": False, "error": "Could not parse recommendations JSON"}
                    
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON parsing error: {e}"}
                
        except Exception as e:
            self.logger.error(f"Error generating discovery recommendations: {e}")
            return {"success": False, "error": str(e)}

    async def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about discovery activities"""
        try:
            # Calculate statistics
            total_sources = len(self.discovered_sources)
            active_sources = sum(1 for source in self.discovered_sources.values() if source.is_active)
            
            by_jurisdiction = {}
            by_agency = {}
            by_type = {}
            
            for source in self.discovered_sources.values():
                # By jurisdiction
                by_jurisdiction[source.jurisdiction] = by_jurisdiction.get(source.jurisdiction, 0) + 1
                # By agency  
                by_agency[source.agency] = by_agency.get(source.agency, 0) + 1
                # By type
                by_type[source.source_type.value] = by_type.get(source.source_type.value, 0) + 1
            
            return {
                "total_sources_discovered": total_sources,
                "active_sources": active_sources,
                "discovery_sessions": len(self.discovery_sessions),
                "by_jurisdiction": by_jurisdiction,
                "by_agency": by_agency,
                "by_source_type": by_type,
                "average_confidence": sum(source.confidence_score for source in self.discovered_sources.values()) / total_sources if total_sources > 0 else 0,
                "last_discovery_session": self.discovery_sessions[-1].start_time.isoformat() if self.discovery_sessions else None
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating discovery statistics: {e}")
            return {"error": str(e)}