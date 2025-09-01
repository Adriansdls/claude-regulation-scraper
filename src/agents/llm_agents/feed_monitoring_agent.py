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
    
    def __init__(self, broker, discovery_agent=None, storage_path: str = "./feed_monitoring_data"):
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
                }
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
        """Parse HTML page using LLM to identify publication items"""
        try:
            # Use LLM to parse HTML for publication items
            parsing_prompt = f"""Analyze this HTML content from a regulatory publication source to identify new publications, regulations, or regulatory updates.

SOURCE URL: {feed_url}
SOURCE ID: {source_id}

HTML CONTENT (first 8000 chars):
{content[:8000]}...

Extract publication items from this page and return in JSON format:

{{
    "publications_found": [
        {{
            "title": "publication title",
            "url": "full URL to the publication",
            "content_snippet": "brief description or summary", 
            "published_date": "date if found (YYYY-MM-DD format)",
            "item_type": "regulation|guidance|alert|news_release|notice",
            "keywords": ["relevant keywords"],
            "relevance_score": 0.0-1.0
        }}
    ],
    "parsing_notes": ["notes about what was found or parsing challenges"]
}}

Look for:
1. Recent publications, news releases, or regulatory announcements
2. Links to specific regulations or guidance documents  
3. Publication dates, effective dates, or "new" indicators
4. Titles and descriptions that indicate regulatory content
5. Government or agency-specific publication patterns

Focus on finding items that appear to be new or recently published regulatory content."""

            context = AgentContext(
                session_id=f"html_parsing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=feed_url,
                metadata={"parsing_type": "html_feed", "source_id": source_id, "url": feed_url}
            )
            
            response = await self.generate_response(parsing_prompt, context)
            
            if response:
                try:
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        parsing_result = json.loads(json_match.group())
                        
                        items = []
                        for pub in parsing_result.get('publications_found', []):
                            # Ensure URL is absolute
                            pub_url = pub.get('url', '')
                            if pub_url and not pub_url.startswith('http'):
                                pub_url = urljoin(feed_url, pub_url)
                            
                            if pub.get('title') and pub_url:
                                item_data = {
                                    "title": pub['title'],
                                    "url": pub_url,
                                    "content_snippet": pub.get('content_snippet', '')[:500],
                                    "published_date": pub.get('published_date'),
                                    "source_id": source_id,
                                    "item_type": pub.get('item_type', 'unknown'),
                                    "keywords": pub.get('keywords', []),
                                    "relevance_score": pub.get('relevance_score', 0.5)
                                }
                                items.append(item_data)
                        
                        return items
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error parsing HTML feed JSON response: {e}")
                    
            return []
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML feed: {e}")
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