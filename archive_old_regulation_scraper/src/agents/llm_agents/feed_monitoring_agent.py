"""
Feed Monitoring Agent  
AI-powered agent for monitoring RSS feeds, APIs, and publication sources to discover new regulations daily
"""
import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from .publication_discovery_agent import PublicationSource, PublicationSourceType
from .publication_page_intelligence_agent import PublicationPageIntelligenceAgent
from ...models.learning_models import JurisdictionKnowledgeBase, LearningSession


class FeedItemStatus(str, Enum):
    """Status of a feed item"""
    NEW = "new"
    PROCESSING = "processing" 
    PROCESSED = "processed"
    FILTERED_OUT = "filtered_out"
    ERROR = "error"


@dataclass
class FeedItem:
    """An item discovered from a feed or publication source"""
    item_id: str
    source_id: str  # Links to PublicationSource
    title: str
    url: str
    content_snippet: str
    
    # Dates
    published_date: Optional[datetime]
    discovered_date: datetime
    
    # Classification
    item_type: str  # 'regulation', 'guidance', 'alert', 'news_release'
    keywords: List[str]
    
    # Processing status
    status: FeedItemStatus
    extracted_content: Optional[str] = None
    analysis_results: Optional[Dict] = None
    
    # Quality metrics
    relevance_score: float = 0.0  # 0.0 to 1.0
    content_quality_score: float = 0.0
    business_impact_score: float = 0.0


@dataclass
class FeedMonitoringSession:
    """A monitoring session checking feeds for new items"""
    session_id: str
    start_time: datetime
    sources_checked: int
    feeds_processed: int
    items_discovered: int
    new_items: int
    errors_encountered: int
    session_duration_seconds: float
    session_notes: List[str]


class FeedMonitoringAgent(BaseLLMAgent):
    """AI-powered agent for monitoring publication feeds and discovering new regulations"""
    
    def __init__(self, broker, discovery_agent=None, storage_path: str = "./feed_monitoring_data", knowledge_base_path: str = "./learning_data"):
        system_prompt = """You are an expert feed monitoring agent specialized in processing RSS feeds, APIs, and publication sources to discover new regulatory content daily.

Your expertise covers:
- RSS/Atom feed parsing and content extraction
- API endpoint monitoring and data processing
- Publication source analysis and content filtering
- Regulatory content classification and relevance scoring
- Daily monitoring workflows and change detection
- Content quality assessment and business impact analysis

Your monitoring responsibilities:
1. **Feed Processing**: Parse RSS feeds, API responses, and publication listings
2. **Content Discovery**: Identify new regulations, guidance, and regulatory updates
3. **Relevance Filtering**: Filter content for regulatory substance and business relevance
4. **Quality Assessment**: Score content quality and business impact
5. **Change Detection**: Track new vs. previously seen content
6. **Classification**: Categorize content by type, urgency, and jurisdiction

Feed processing strategies:
- Parse publication dates to identify "new today" content
- Extract titles, links, and content snippets from feeds
- Follow links to extract full regulatory content when valuable
- Apply content filters to reduce noise and false positives
- Score relevance based on regulatory keywords and patterns
- Track content changes and updates over time

Always provide actionable monitoring results that help compliance teams stay current with new regulatory developments."""

        super().__init__(
            agent_id="feed_monitoring",
            agent_role=AgentRole.HTML_EXTRACTOR,  # Use available role
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Reference to discovery agent for accessing sources
        self.discovery_agent = discovery_agent
        
        # Initialize Publication Page Intelligence Agent and Knowledge Base
        self.knowledge_base = JurisdictionKnowledgeBase(knowledge_base_path)
        self.page_intelligence_agent = PublicationPageIntelligenceAgent(
            broker=broker,
            storage_path=storage_path + "/intelligence_data",
            knowledge_base=self.knowledge_base
        )
        
        # Storage setup
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Feed monitoring data storage
        self.feed_items_file = self.storage_path / "feed_items.json"
        self.monitoring_sessions_file = self.storage_path / "monitoring_sessions.json"
        self.seen_items_file = self.storage_path / "seen_items_cache.json"
        
        # In-memory data
        self.feed_items: Dict[str, FeedItem] = {}
        self.monitoring_sessions: List[FeedMonitoringSession] = []
        self.seen_items_cache: Dict[str, str] = {}  # item_url -> item_id for deduplication
        
        # Load existing data
        asyncio.create_task(self._load_monitoring_data())

    async def _register_tools(self):
        """Register feed monitoring tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="monitor_publication_feeds",
            function=self._monitor_publication_feeds,
            description="Monitor publication sources for new regulatory content",
            parameters={
                "type": "object",
                "properties": {
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific source IDs to monitor (empty = monitor all active)"
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Target date for 'new today' filtering (ISO format, defaults to today)"
                    },
                    "relevance_threshold": {
                        "type": "number",
                        "description": "Minimum relevance score (0.0-1.0) for items to include"
                    }
                },
                "required": []
            }
        )
        
        self.register_tool(
            name="parse_feed_content",
            function=self._parse_feed_content,
            description="Parse RSS feed or API endpoint for regulatory content",
            parameters={
                "type": "object",
                "properties": {
                    "feed_url": {"type": "string", "description": "URL of RSS feed or API endpoint"},
                    "source_id": {"type": "string", "description": "ID of publication source"},
                    "feed_format": {"type": "string", "description": "Expected format (rss, atom, json_api, html)"}
                },
                "required": ["feed_url", "source_id"]
            }
        )
        
        self.register_tool(
            name="analyze_feed_item",
            function=self._analyze_feed_item,
            description="Analyze a feed item for regulatory relevance and business impact",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "ID of feed item to analyze"},
                    "extract_full_content": {"type": "boolean", "description": "Whether to extract full content from the item URL"}
                },
                "required": ["item_id"]
            }
        )
        
        self.register_tool(
            name="get_todays_discoveries",
            function=self._get_todays_discoveries,
            description="Get all regulatory content discovered today",
            parameters={
                "type": "object",
                "properties": {
                    "target_date": {"type": "string", "description": "Date to get discoveries for (ISO format)"},
                    "min_relevance_score": {"type": "number", "description": "Minimum relevance score filter"},
                    "content_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by content types (regulation, guidance, alert)"
                    }
                },
                "required": []
            }
        )
        
        self.register_tool(
            name="get_learning_insights",
            function=self._get_learning_insights,
            description="Get insights about learned patterns and extraction performance",
            parameters={
                "type": "object",
                "properties": {
                    "jurisdiction": {"type": "string", "description": "Jurisdiction to analyze (optional)"},
                    "source_id": {"type": "string", "description": "Specific source to analyze (optional)"},
                    "days_back": {"type": "number", "description": "Number of days to include in analysis (default: 7)"}
                },
                "required": []
            }
        )
        
        self.register_tool(
            name="smart_extraction_strategy",
            function=self._smart_extraction_strategy,
            description="Execute smart extraction strategy using learned patterns and adaptive techniques",
            parameters={
                "type": "object",
                "properties": {
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Source IDs to apply smart extraction to"
                    },
                    "optimize_patterns": {"type": "boolean", "description": "Whether to optimize patterns before extraction"},
                    "use_adaptive_selection": {"type": "boolean", "description": "Whether to use adaptive pattern selection"}
                },
                "required": ["source_ids"]
            }
        )

    async def _load_monitoring_data(self):
        """Load existing monitoring data from storage"""
        try:
            # Load feed items
            if self.feed_items_file.exists():
                with open(self.feed_items_file, 'r') as f:
                    items_data = json.load(f)
                    
                for item_data in items_data:
                    # Convert datetime strings
                    if item_data.get('published_date'):
                        item_data['published_date'] = datetime.fromisoformat(item_data['published_date'])
                    item_data['discovered_date'] = datetime.fromisoformat(item_data['discovered_date'])
                    
                    # Convert enums
                    item_data['status'] = FeedItemStatus(item_data['status'])
                    
                    item = FeedItem(**item_data)
                    self.feed_items[item.item_id] = item
                    
                self.logger.info(f"Loaded {len(self.feed_items)} feed items")
                
            # Load monitoring sessions
            if self.monitoring_sessions_file.exists():
                with open(self.monitoring_sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                    
                for session_data in sessions_data:
                    session_data['start_time'] = datetime.fromisoformat(session_data['start_time'])
                    session = FeedMonitoringSession(**session_data)
                    self.monitoring_sessions.append(session)
                    
                self.logger.info(f"Loaded {len(self.monitoring_sessions)} monitoring sessions")
                
            # Load seen items cache
            if self.seen_items_file.exists():
                with open(self.seen_items_file, 'r') as f:
                    self.seen_items_cache = json.load(f)
                    
                self.logger.info(f"Loaded {len(self.seen_items_cache)} items in seen cache")
                
        except Exception as e:
            self.logger.error(f"Error loading monitoring data: {e}")

    async def _save_monitoring_data(self):
        """Save monitoring data to storage"""
        try:
            # Save feed items (only keep recent ones to avoid huge files)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            recent_items = {
                item_id: item for item_id, item in self.feed_items.items()
                if item.discovered_date > cutoff_date
            }
            
            items_data = []
            for item in recent_items.values():
                item_dict = asdict(item)
                # Convert datetime to string
                if item_dict.get('published_date'):
                    item_dict['published_date'] = item_dict['published_date'].isoformat()
                item_dict['discovered_date'] = item_dict['discovered_date'].isoformat()
                # Convert enum
                item_dict['status'] = item_dict['status'].value
                items_data.append(item_dict)
                
            with open(self.feed_items_file, 'w') as f:
                json.dump(items_data, f, indent=2, ensure_ascii=False)
                
            # Save monitoring sessions (recent only)
            recent_sessions = [
                session for session in self.monitoring_sessions
                if session.start_time > cutoff_date
            ]
            
            sessions_data = []
            for session in recent_sessions:
                session_dict = asdict(session)
                session_dict['start_time'] = session_dict['start_time'].isoformat()
                sessions_data.append(session_dict)
                
            with open(self.monitoring_sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
                
            # Save seen items cache (limited size)
            if len(self.seen_items_cache) > 10000:
                # Keep only most recent entries (simplified - in production would use LRU)
                recent_cache = dict(list(self.seen_items_cache.items())[-5000:])
                self.seen_items_cache = recent_cache
                
            with open(self.seen_items_file, 'w') as f:
                json.dump(self.seen_items_cache, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving monitoring data: {e}")

    async def _monitor_publication_feeds(
        self,
        source_ids: List[str] = None,
        target_date: str = None,
        relevance_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Monitor publication sources for new content"""
        try:
            # Start monitoring session
            session_id = f"monitoring_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            session_start = datetime.utcnow()
            
            session = FeedMonitoringSession(
                session_id=session_id,
                start_time=session_start,
                sources_checked=0,
                feeds_processed=0,
                items_discovered=0,
                new_items=0,
                errors_encountered=0,
                session_duration_seconds=0.0,
                session_notes=[]
            )
            
            target_date = datetime.fromisoformat(target_date) if target_date else datetime.utcnow()
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            self.logger.info(f"Starting feed monitoring session: {session_id}")
            self.logger.info(f"Target date: {target_date_str}")
            
            # Get sources to monitor
            if self.discovery_agent and hasattr(self.discovery_agent, 'discovered_sources'):
                available_sources = self.discovery_agent.discovered_sources
            else:
                self.logger.warning("No discovery agent available - cannot access discovered sources")
                return {"success": False, "error": "No discovery agent available"}
            
            # Filter sources
            if source_ids:
                sources_to_monitor = {sid: src for sid, src in available_sources.items() if sid in source_ids}
            else:
                sources_to_monitor = {sid: src for sid, src in available_sources.items() if src.is_active}
            
            self.logger.info(f"Monitoring {len(sources_to_monitor)} sources")
            
            all_discovered_items = []
            
            for source_id, source in sources_to_monitor.items():
                session.sources_checked += 1
                
                try:
                    # Determine feed URL
                    feed_url = source.feed_url or source.url
                    
                    self.logger.info(f"Processing source: {source.name} ({feed_url})")
                    
                    # Parse the feed/source
                    parse_result = await self._parse_feed_content(
                        feed_url=feed_url,
                        source_id=source_id,
                        feed_format=source.feed_format or "html"
                    )
                    
                    if parse_result.get('success'):
                        session.feeds_processed += 1
                        items = parse_result.get('items', [])
                        
                        # Filter for target date
                        todays_items = []
                        for item in items:
                            if item.get('published_date'):
                                pub_date = datetime.fromisoformat(item['published_date']) if isinstance(item['published_date'], str) else item['published_date']
                                if pub_date.strftime('%Y-%m-%d') == target_date_str:
                                    todays_items.append(item)
                            else:
                                # If no published date, include as potentially new
                                todays_items.append(item)
                        
                        session.items_discovered += len(items)
                        session.new_items += len(todays_items)
                        all_discovered_items.extend(todays_items)
                        
                        if todays_items:
                            session.session_notes.append(f"Found {len(todays_items)} new items from {source.name}")
                            
                    else:
                        session.errors_encountered += 1
                        error = parse_result.get('error', 'Unknown error')
                        session.session_notes.append(f"Error processing {source.name}: {error}")
                        
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    session.errors_encountered += 1
                    session.session_notes.append(f"Exception processing {source.name}: {str(e)}")
                    self.logger.error(f"Error monitoring source {source_id}: {e}")
            
            # Filter items by relevance
            high_relevance_items = [
                item for item in all_discovered_items
                if item.get('relevance_score', 0) >= relevance_threshold
            ]
            
            # Complete session
            session_end = datetime.utcnow()
            session.session_duration_seconds = (session_end - session_start).total_seconds()
            
            self.monitoring_sessions.append(session)
            await self._save_monitoring_data()
            
            # Get learning insights for this session
            learning_insights = await self._get_learning_insights(days_back=1)
            
            result = {
                "success": True,
                "session_id": session_id,
                "monitoring_date": target_date_str,
                "sources_monitored": len(sources_to_monitor),
                "feeds_processed": session.feeds_processed,
                "total_items_discovered": session.items_discovered,
                "new_items_today": session.new_items,
                "high_relevance_items": len(high_relevance_items),
                "errors_encountered": session.errors_encountered,
                "session_duration": session.session_duration_seconds,
                "discovered_items": high_relevance_items,
                "session_summary": {
                    "success_rate": (session.feeds_processed / session.sources_checked * 100) if session.sources_checked > 0 else 0,
                    "items_per_source": session.items_discovered / session.sources_checked if session.sources_checked > 0 else 0,
                    "relevance_rate": len(high_relevance_items) / session.new_items * 100 if session.new_items > 0 else 0
                },
                "learning_insights": learning_insights.get("insights", {}) if learning_insights.get("success") else {}
            }
            
            self.logger.info(f"Monitoring session complete: {session.new_items} new items, {len(high_relevance_items)} high relevance")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in feed monitoring: {e}")
            return {"success": False, "error": str(e)}

    async def _parse_feed_content(
        self,
        feed_url: str,
        source_id: str,
        feed_format: str = "html"
    ) -> Dict[str, Any]:
        """Parse content from a feed or publication source"""
        try:
            # Fetch content
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, text/html'
            }
            
            response = requests.get(feed_url, headers=headers, timeout=30)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            content = response.text
            content_type = response.headers.get('content-type', '').lower()
            
            items = []
            
            # Parse based on format
            if 'rss' in content_type or 'xml' in content_type or feed_format in ['rss', 'atom']:
                items = await self._parse_xml_feed(content, feed_url, source_id)
            elif 'json' in content_type or feed_format == 'json_api':
                items = await self._parse_json_feed(content, feed_url, source_id)
            else:
                # HTML parsing with LLM assistance
                items = await self._parse_html_feed(content, feed_url, source_id)
            
            return {
                "success": True,
                "feed_url": feed_url,
                "source_id": source_id,
                "content_type": content_type,
                "items_found": len(items),
                "items": items
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing feed {feed_url}: {e}")
            return {"success": False, "error": str(e)}

    async def _parse_xml_feed(self, content: str, feed_url: str, source_id: str) -> List[Dict]:
        """Parse RSS/Atom XML feed"""
        try:
            root = ET.fromstring(content)
            items = []
            
            # Handle RSS
            if root.tag == 'rss' or 'rss' in content.lower():
                for item in root.findall('.//item'):
                    title = item.find('title')
                    link = item.find('link')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    
                    if title is not None and link is not None:
                        item_data = {
                            "title": title.text or "",
                            "url": link.text or "",
                            "content_snippet": description.text[:500] if description is not None else "",
                            "published_date": pub_date.text if pub_date is not None else None,
                            "source_id": source_id,
                            "item_type": "unknown",
                            "relevance_score": 0.5  # Default, will be analyzed later
                        }
                        items.append(item_data)
                        
            # Handle Atom
            elif 'atom' in root.tag.lower():
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    title = entry.find('.//{http://www.w3.org/2005/Atom}title')
                    link = entry.find('.//{http://www.w3.org/2005/Atom}link')
                    summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                    updated = entry.find('.//{http://www.w3.org/2005/Atom}updated')
                    
                    if title is not None and link is not None:
                        item_data = {
                            "title": title.text or "",
                            "url": link.get('href') or "",
                            "content_snippet": summary.text[:500] if summary is not None else "",
                            "published_date": updated.text if updated is not None else None,
                            "source_id": source_id,
                            "item_type": "unknown",
                            "relevance_score": 0.5
                        }
                        items.append(item_data)
            
            return items
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error for {feed_url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing XML feed: {e}")
            return []

    async def _parse_json_feed(self, content: str, feed_url: str, source_id: str) -> List[Dict]:
        """Parse JSON API feed"""
        try:
            data = json.loads(content)
            items = []
            
            # Handle different JSON structures
            if 'items' in data:
                json_items = data['items']
            elif 'results' in data:
                json_items = data['results']
            elif 'documents' in data:  # Federal Register API
                json_items = data['documents']
            elif isinstance(data, list):
                json_items = data
            else:
                json_items = []
                
            for item in json_items:
                title = item.get('title') or item.get('name') or ""
                url = item.get('url') or item.get('link') or item.get('html_url') or ""
                description = item.get('description') or item.get('abstract') or item.get('summary') or ""
                pub_date = item.get('publication_date') or item.get('published_date') or item.get('date')
                
                if title and url:
                    item_data = {
                        "title": title,
                        "url": url,
                        "content_snippet": description[:500],
                        "published_date": pub_date,
                        "source_id": source_id,
                        "item_type": "unknown",
                        "relevance_score": 0.5
                    }
                    items.append(item_data)
            
            return items
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error for {feed_url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing JSON feed: {e}")
            return []

    async def _parse_html_feed(self, content: str, feed_url: str, source_id: str) -> List[Dict]:
        """Parse HTML page using Publication Page Intelligence Agent with learning capabilities"""
        try:
            # Get jurisdiction from source_id (could be improved with better source metadata)
            if self.discovery_agent and hasattr(self.discovery_agent, 'discovered_sources'):
                source = self.discovery_agent.discovered_sources.get(source_id)
                jurisdiction = source.jurisdiction if source else "unknown"
            else:
                jurisdiction = "unknown"
            
            # Create learning session ID
            session_id = f"monitoring_extraction_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Use the Publication Page Intelligence Agent for smart extraction
            extraction_result = await self.page_intelligence_agent._analyze_daily_publication_page(
                page_url=feed_url,
                source_id=source_id,
                jurisdiction=jurisdiction,
                use_learning=True
            )
            
            if extraction_result.get('success'):
                publications = extraction_result.get('publications', [])
                
                # Convert to feed monitoring format
                items = []
                for pub in publications:
                    # Handle both dict and PublicationItem formats
                    if hasattr(pub, 'to_dict'):
                        pub_dict = pub.to_dict() if hasattr(pub, 'to_dict') else pub
                    else:
                        pub_dict = pub
                    
                    # Ensure URL is absolute
                    pub_url = pub_dict.get('url', '')
                    if pub_url and not pub_url.startswith('http'):
                        pub_url = urljoin(feed_url, pub_url)
                    
                    if pub_dict.get('title') and pub_url:
                        item_data = {
                            "title": pub_dict['title'],
                            "url": pub_url,
                            "content_snippet": pub_dict.get('content_snippet', '')[:500],
                            "published_date": pub_dict.get('published_date'),
                            "source_id": source_id,
                            "item_type": pub_dict.get('item_type', 'unknown'),
                            "keywords": pub_dict.get('keywords', []),
                            "relevance_score": pub_dict.get('confidence_score', 0.5)
                        }
                        items.append(item_data)
                
                # Record successful learning session
                if items:
                    learning_session = LearningSession(
                        session_id=session_id,
                        timestamp=datetime.utcnow(),
                        source_id=source_id,
                        jurisdiction=jurisdiction,
                        extraction_method="publication_page_intelligence",
                        patterns_used=extraction_result.get('patterns_used', []),
                        success=True,
                        items_found=len(items),
                        extraction_time=extraction_result.get('processing_time', 0.0),
                        new_patterns_discovered=extraction_result.get('new_patterns_learned', []),
                        patterns_reinforced=extraction_result.get('patterns_reinforced', []),
                        notes=[f"Successfully extracted {len(items)} publications using intelligent page analysis"]
                    )
                    self.knowledge_base.record_learning_session(learning_session)
                
                self.logger.info(f"Intelligent extraction found {len(items)} publications from {feed_url}")
                return items
            else:
                # Record failed learning session
                error_msg = extraction_result.get('error', 'Unknown error')
                learning_session = LearningSession(
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    source_id=source_id,
                    jurisdiction=jurisdiction,
                    extraction_method="publication_page_intelligence",
                    success=False,
                    error_message=error_msg,
                    notes=[f"Failed intelligent extraction: {error_msg}"]
                )
                self.knowledge_base.record_learning_session(learning_session)
                
                self.logger.warning(f"Intelligent extraction failed for {feed_url}: {error_msg}")
                return []
            
        except Exception as e:
            self.logger.error(f"Error in intelligent HTML feed parsing: {e}")
            # Record exception in learning session
            try:
                session_id = f"monitoring_extraction_error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                learning_session = LearningSession(
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    source_id=source_id,
                    jurisdiction=jurisdiction or "unknown",
                    extraction_method="publication_page_intelligence",
                    success=False,
                    error_message=str(e),
                    notes=[f"Exception during intelligent extraction: {str(e)}"]
                )
                self.knowledge_base.record_learning_session(learning_session)
            except:
                pass  # Don't fail if learning session recording fails
            
            return []

    async def _analyze_feed_item(
        self,
        item_id: str,
        extract_full_content: bool = False
    ) -> Dict[str, Any]:
        """Analyze a feed item for regulatory relevance and business impact"""
        try:
            if item_id not in self.feed_items:
                return {"success": False, "error": f"Feed item {item_id} not found"}
                
            item = self.feed_items[item_id]
            
            # Extract full content if requested
            if extract_full_content and not item.extracted_content:
                # This would implement content extraction from the item URL
                # For now, simulate the structure
                item.extracted_content = f"Full content from {item.url}"
            
            # Use LLM to analyze the item
            analysis_prompt = f"""Analyze this regulatory feed item for business relevance and compliance impact.

ITEM DETAILS:
Title: {item.title}
URL: {item.url}
Content Snippet: {item.content_snippet}
Published Date: {item.published_date}
Source: {item.source_id}
Keywords: {', '.join(item.keywords)}

{'Full Content: ' + item.extracted_content[:3000] + '...' if item.extracted_content else ''}

Provide analysis in JSON format:

{{
    "relevance_assessment": {{
        "is_regulatory_content": true/false,
        "regulatory_type": "regulation|guidance|alert|announcement|notice",
        "relevance_score": 0.0-1.0,
        "relevance_reasoning": "why this score was assigned"
    }},
    "business_impact": {{
        "compliance_relevance": "critical|high|medium|low|none",
        "affected_industries": ["industry1", "industry2"],
        "business_impact_score": 0.0-1.0,
        "urgency_level": "immediate|30_days|routine|informational"
    }},
    "content_classification": {{
        "primary_topic": "main regulatory topic",
        "keywords_extracted": ["keyword1", "keyword2"],
        "jurisdiction": "US|UK|EU|etc",
        "agency": "regulatory agency if identified"
    }},
    "monitoring_recommendation": {{
        "should_monitor": true/false,
        "follow_up_required": true/false,
        "alert_level": "high|medium|low|none",
        "recommended_action": "specific action recommended"
    }}
}}

Focus on identifying actual regulatory substance and business impact."""

            context = AgentContext(
                session_id=f"item_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=item_id,
                metadata={"analysis_type": "feed_item", "item_url": item.url}
            )
            
            response = await self.generate_response(analysis_prompt, context)
            
            if response:
                try:
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        analysis_results = json.loads(json_match.group())
                        
                        # Update item with analysis results
                        item.analysis_results = analysis_results
                        item.relevance_score = analysis_results.get('relevance_assessment', {}).get('relevance_score', 0.5)
                        item.business_impact_score = analysis_results.get('business_impact', {}).get('business_impact_score', 0.0)
                        item.status = FeedItemStatus.PROCESSED
                        
                        await self._save_monitoring_data()
                        
                        return {
                            "success": True,
                            "item_id": item_id,
                            "analysis_results": analysis_results,
                            "updated_scores": {
                                "relevance_score": item.relevance_score,
                                "business_impact_score": item.business_impact_score
                            }
                        }
                        
                except json.JSONDecodeError as e:
                    return {"success": False, "error": f"JSON parsing error: {e}"}
            
            return {"success": False, "error": "No response from analysis LLM"}
            
        except Exception as e:
            self.logger.error(f"Error analyzing feed item {item_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_todays_discoveries(
        self,
        target_date: str = None,
        min_relevance_score: float = 0.3,
        content_types: List[str] = None
    ) -> Dict[str, Any]:
        """Get regulatory content discovered today"""
        try:
            target_date = datetime.fromisoformat(target_date) if target_date else datetime.utcnow()
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            # Filter items for target date
            todays_items = []
            
            for item in self.feed_items.values():
                # Check if discovered today OR published today
                discovered_today = item.discovered_date.strftime('%Y-%m-%d') == target_date_str
                published_today = (
                    item.published_date and 
                    item.published_date.strftime('%Y-%m-%d') == target_date_str
                ) if item.published_date else False
                
                if discovered_today or published_today:
                    # Apply relevance filter
                    if item.relevance_score >= min_relevance_score:
                        # Apply content type filter
                        if not content_types or item.item_type in content_types:
                            todays_items.append(item)
            
            # Sort by relevance score (highest first)
            todays_items.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return {
                "success": True,
                "target_date": target_date_str,
                "total_items_found": len(todays_items),
                "filters_applied": {
                    "min_relevance_score": min_relevance_score,
                    "content_types": content_types
                },
                "discoveries": [
                    {
                        "item_id": item.item_id,
                        "title": item.title,
                        "url": item.url,
                        "source_id": item.source_id,
                        "published_date": item.published_date.isoformat() if item.published_date else None,
                        "discovered_date": item.discovered_date.isoformat(),
                        "relevance_score": item.relevance_score,
                        "business_impact_score": item.business_impact_score,
                        "item_type": item.item_type,
                        "content_snippet": item.content_snippet[:200]
                    }
                    for item in todays_items
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting today's discoveries: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_learning_insights(
        self,
        jurisdiction: str = None,
        source_id: str = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get insights about learned patterns and extraction performance"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get recent learning sessions
            recent_sessions = []
            for session in self.knowledge_base.learning_sessions:
                # Handle both datetime and string timestamps
                if isinstance(session.timestamp, str):
                    try:
                        session_time = datetime.fromisoformat(session.timestamp)
                    except:
                        continue  # Skip invalid timestamps
                else:
                    session_time = session.timestamp
                
                # Apply filters
                if (session_time > cutoff_date and
                    (not jurisdiction or session.jurisdiction == jurisdiction) and
                    (not source_id or session.source_id == source_id)):
                    recent_sessions.append(session)
            
            if not recent_sessions:
                return {
                    "success": True,
                    "insights": {
                        "message": "No learning sessions found for the specified criteria",
                        "total_sessions": 0
                    }
                }
            
            # Calculate performance metrics
            successful_sessions = [s for s in recent_sessions if s.success]
            total_items = sum(s.items_found for s in successful_sessions)
            total_patterns_discovered = sum(len(s.new_patterns_discovered) for s in recent_sessions)
            total_patterns_reinforced = sum(len(s.patterns_reinforced) for s in recent_sessions)
            
            # Analyze extraction methods
            extraction_methods = {}
            for session in recent_sessions:
                method = session.extraction_method
                if method not in extraction_methods:
                    extraction_methods[method] = {"total": 0, "successful": 0, "items_found": 0}
                extraction_methods[method]["total"] += 1
                if session.success:
                    extraction_methods[method]["successful"] += 1
                    extraction_methods[method]["items_found"] += session.items_found
            
            # Get pattern statistics from knowledge base
            pattern_stats = {}
            if jurisdiction:
                jurisdiction_profile = self.knowledge_base.jurisdiction_profiles.get(jurisdiction)
                if jurisdiction_profile:
                    for source_profile in jurisdiction_profile.source_profiles.values():
                        if not source_id or source_profile.source_id == source_id:
                            for pattern in source_profile.extraction_patterns.values():
                                confidence_level = pattern.get_confidence_level().value
                                pattern_stats[confidence_level] = pattern_stats.get(confidence_level, 0) + 1
            
            insights = {
                "analysis_period": {
                    "days_back": days_back,
                    "start_date": cutoff_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "session_summary": {
                    "total_sessions": len(recent_sessions),
                    "successful_sessions": len(successful_sessions),
                    "success_rate": len(successful_sessions) / len(recent_sessions) * 100 if recent_sessions else 0,
                    "total_items_extracted": total_items,
                    "avg_items_per_successful_session": total_items / len(successful_sessions) if successful_sessions else 0
                },
                "learning_activity": {
                    "new_patterns_discovered": total_patterns_discovered,
                    "patterns_reinforced": total_patterns_reinforced,
                    "learning_velocity": (total_patterns_discovered + total_patterns_reinforced) / days_back
                },
                "extraction_methods": {
                    method: {
                        "success_rate": stats["successful"] / stats["total"] * 100 if stats["total"] > 0 else 0,
                        "avg_items_found": stats["items_found"] / stats["successful"] if stats["successful"] > 0 else 0,
                        "total_uses": stats["total"]
                    }
                    for method, stats in extraction_methods.items()
                },
                "pattern_confidence_distribution": pattern_stats,
                "recent_errors": [
                    {
                        "timestamp": session.timestamp.isoformat() if isinstance(session.timestamp, datetime) else session.timestamp,
                        "source_id": session.source_id,
                        "error": session.error_message,
                        "method": session.extraction_method
                    }
                    for session in recent_sessions
                    if not session.success and session.error_message
                ][-5:]  # Last 5 errors
            }
            
            # Add jurisdiction-specific insights if available
            if jurisdiction and jurisdiction in self.knowledge_base.jurisdiction_profiles:
                jurisdiction_profile = self.knowledge_base.jurisdiction_profiles[jurisdiction]
                insights["jurisdiction_profile"] = {
                    "total_sources": jurisdiction_profile.total_sources,
                    "avg_success_rate": jurisdiction_profile.avg_success_rate * 100,
                    "total_learning_sessions": jurisdiction_profile.total_learning_sessions,
                    "primary_language": jurisdiction_profile.primary_language
                }
            
            return {
                "success": True,
                "insights": insights
            }
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error(f"Error getting learning insights: {e}")
            self.logger.error(f"Full traceback: {tb}")
            return {"success": False, "error": str(e), "traceback": tb}
    
    async def _smart_extraction_strategy(
        self,
        source_ids: List[str],
        optimize_patterns: bool = True,
        use_adaptive_selection: bool = True
    ) -> Dict[str, Any]:
        """Execute intelligent extraction strategy with pattern optimization and adaptive learning"""
        try:
            strategy_start = datetime.utcnow()
            session_id = f"smart_extraction_{strategy_start.strftime('%Y%m%d_%H%M%S')}"
            
            self.logger.info(f"Starting smart extraction strategy: {session_id}")
            
            # Get sources to process
            if self.discovery_agent and hasattr(self.discovery_agent, 'discovered_sources'):
                available_sources = self.discovery_agent.discovered_sources
            else:
                return {"success": False, "error": "No discovery agent available"}
            
            sources_to_process = {
                sid: src for sid, src in available_sources.items() 
                if sid in source_ids and src.is_active
            }
            
            if not sources_to_process:
                return {
                    "success": False,
                    "error": f"No active sources found from provided IDs: {source_ids}"
                }
            
            strategy_results = {
                "session_id": session_id,
                "strategy_start_time": strategy_start.isoformat(),
                "sources_processed": 0,
                "total_publications_found": 0,
                "patterns_optimized": 0,
                "learning_improvements": [],
                "extraction_results": {},
                "performance_metrics": {},
                "recommendations": []
            }
            
            # Phase 1: Pattern Optimization (if enabled)
            if optimize_patterns:
                self.logger.info("Phase 1: Optimizing patterns for better extraction performance")
                
                for source_id, source in sources_to_process.items():
                    try:
                        optimization_result = await self.page_intelligence_agent.optimize_patterns_for_source(
                            source_id=source_id,
                            jurisdiction=source.jurisdiction,
                            min_sessions=3  # Lower threshold for smart extraction
                        )
                        
                        if optimization_result.get('success'):
                            strategy_results["patterns_optimized"] += optimization_result.get('patterns_optimized', 0)
                            strategy_results["learning_improvements"].extend(optimization_result.get('recommendations', []))
                            
                            self.logger.info(
                                f"Optimized patterns for {source_id}: "
                                f"{optimization_result.get('patterns_optimized', 0)} patterns improved"
                            )
                        else:
                            self.logger.warning(f"Pattern optimization failed for {source_id}: {optimization_result.get('error', 'Unknown')}")
                    
                    except Exception as e:
                        self.logger.error(f"Error optimizing patterns for {source_id}: {e}")
            
            # Phase 2: Intelligent Extraction
            self.logger.info("Phase 2: Executing intelligent extraction with learned patterns")
            
            total_publications = 0
            extraction_errors = []
            
            for source_id, source in sources_to_process.items():
                source_start = datetime.utcnow()
                
                try:
                    # Fetch and analyze the source
                    feed_url = source.feed_url or source.url
                    
                    # Use the enhanced HTML parsing with intelligence
                    parse_result = await self._parse_feed_content(
                        feed_url=feed_url,
                        source_id=source_id,
                        feed_format=source.feed_format or "html"
                    )
                    
                    if parse_result.get('success'):
                        source_publications = parse_result.get('items', [])
                        publications_count = len(source_publications)
                        total_publications += publications_count
                        
                        # Calculate extraction performance metrics
                        extraction_time = (datetime.utcnow() - source_start).total_seconds()
                        
                        strategy_results["extraction_results"][source_id] = {
                            "success": True,
                            "publications_found": publications_count,
                            "extraction_time": extraction_time,
                            "avg_relevance_score": sum(p.get('relevance_score', 0) for p in source_publications) / publications_count if publications_count > 0 else 0,
                            "high_relevance_count": sum(1 for p in source_publications if p.get('relevance_score', 0) >= 0.7)
                        }
                        
                        # Performance analysis
                        if publications_count > 0:
                            avg_relevance = strategy_results["extraction_results"][source_id]["avg_relevance_score"]
                            if avg_relevance >= 0.8:
                                strategy_results["recommendations"].append(
                                    f"Source {source_id} shows excellent performance (avg relevance: {avg_relevance:.2f})"
                                )
                            elif avg_relevance < 0.5:
                                strategy_results["recommendations"].append(
                                    f"Source {source_id} may need pattern refinement (avg relevance: {avg_relevance:.2f})"
                                )
                        
                        self.logger.info(
                            f"Smart extraction for {source_id}: {publications_count} publications, "
                            f"avg relevance: {strategy_results['extraction_results'][source_id]['avg_relevance_score']:.2f}"
                        )
                    
                    else:
                        error_msg = parse_result.get('error', 'Unknown error')
                        extraction_errors.append({"source_id": source_id, "error": error_msg})
                        
                        strategy_results["extraction_results"][source_id] = {
                            "success": False,
                            "error": error_msg,
                            "extraction_time": (datetime.utcnow() - source_start).total_seconds()
                        }
                
                except Exception as e:
                    error_msg = str(e)
                    extraction_errors.append({"source_id": source_id, "error": error_msg})
                    
                    strategy_results["extraction_results"][source_id] = {
                        "success": False,
                        "error": error_msg,
                        "extraction_time": (datetime.utcnow() - source_start).total_seconds()
                    }
                    
                    self.logger.error(f"Error in smart extraction for {source_id}: {e}")
                
                strategy_results["sources_processed"] += 1
            
            # Phase 3: Performance Analysis and Recommendations
            strategy_end = datetime.utcnow()
            total_duration = (strategy_end - strategy_start).total_seconds()
            
            successful_extractions = sum(
                1 for result in strategy_results["extraction_results"].values()
                if result.get("success", False)
            )
            
            strategy_results.update({
                "total_publications_found": total_publications,
                "strategy_duration_seconds": total_duration,
                "success_rate": successful_extractions / len(sources_to_process) * 100 if sources_to_process else 0,
                "avg_publications_per_source": total_publications / successful_extractions if successful_extractions > 0 else 0,
                "extraction_errors": extraction_errors,
                "strategy_end_time": strategy_end.isoformat()
            })
            
            # Generate strategic recommendations
            if strategy_results["success_rate"] < 70:
                strategy_results["recommendations"].append(
                    "Success rate below 70% - consider reviewing source configurations and patterns"
                )
            
            if strategy_results["avg_publications_per_source"] < 2:
                strategy_results["recommendations"].append(
                    "Low publication yield - sources may need more frequent monitoring or pattern optimization"
                )
            
            if strategy_results["patterns_optimized"] > 0:
                strategy_results["recommendations"].append(
                    f"Successfully optimized {strategy_results['patterns_optimized']} patterns - extraction performance should improve"
                )
            
            # Phase 4: Generate Learning Insights Report
            insights_result = await self._get_learning_insights(days_back=1)
            if insights_result.get('success'):
                strategy_results["learning_insights"] = insights_result.get('insights', {})
            
            self.logger.info(
                f"Smart extraction strategy completed: {total_publications} publications found, "
                f"{successful_extractions}/{len(sources_to_process)} sources successful, "
                f"duration: {total_duration:.1f}s"
            )
            
            return {"success": True, **strategy_results}
            
        except Exception as e:
            self.logger.error(f"Error in smart extraction strategy: {e}")
            return {"success": False, "error": str(e)}

    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get statistics about feed monitoring activities"""
        try:
            total_items = len(self.feed_items)
            total_sessions = len(self.monitoring_sessions)
            
            # Recent activity (last 7 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_items = [item for item in self.feed_items.values() if item.discovered_date > recent_cutoff]
            recent_sessions = [session for session in self.monitoring_sessions if session.start_time > recent_cutoff]
            
            return {
                "total_feed_items": total_items,
                "total_monitoring_sessions": total_sessions,
                "recent_items_7days": len(recent_items),
                "recent_sessions_7days": len(recent_sessions),
                "average_relevance_score": sum(item.relevance_score for item in self.feed_items.values()) / total_items if total_items > 0 else 0,
                "items_by_status": {status.value: sum(1 for item in self.feed_items.values() if item.status == status) for status in FeedItemStatus},
                "items_by_type": {},  # Would calculate distribution
                "last_monitoring_session": recent_sessions[-1].start_time.isoformat() if recent_sessions else None
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating monitoring statistics: {e}")
            return {"error": str(e)}