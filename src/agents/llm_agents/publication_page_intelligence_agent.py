"""
Publication Page Intelligence Agent
Advanced LLM-powered agent for analyzing daily publication pages with learning capabilities
"""
import asyncio
import logging
import json
import re
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.learning_models import (
    JurisdictionKnowledgeBase, 
    SourceProfile, 
    ExtractionPattern, 
    PatternType, 
    LearningSession,
    ExtractionConfidence
)


@dataclass
class PublicationItem:
    """An item found on a daily publication page"""
    title: str
    url: str
    published_date: Optional[datetime] = None
    content_snippet: str = ""
    item_type: str = "regulation"
    confidence_score: float = 0.5
    extraction_method: str = "unknown"
    source_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "content_snippet": self.content_snippet,
            "item_type": self.item_type,
            "confidence_score": self.confidence_score,
            "extraction_method": self.extraction_method,
            "source_id": self.source_id
        }


class PublicationPageIntelligenceAgent(BaseLLMAgent):
    """AI-powered agent for intelligent analysis of daily publication pages with learning"""
    
    def __init__(self, broker, storage_path: str = "./intelligence_data", knowledge_base=None):
        system_prompt = """You are an expert Publication Page Intelligence Agent specialized in analyzing regulatory publication websites to extract today's new regulations and publications.

Your core expertise:
- Analyze HTML content to find daily publication sections
- Extract publication links, titles, dates, and metadata  
- Identify patterns in how different jurisdictions organize daily publications
- Learn from successful extractions to improve future performance
- Handle different languages, date formats, and page structures
- Focus on TODAY's publications, avoiding historical archives

Your intelligence capabilities:
- Pattern Recognition: Identify CSS selectors and page structures that work
- Learning: Remember successful extraction methods for reuse
- Adaptation: Adjust strategies based on what works for each jurisdiction
- Date Intelligence: Parse dates in various formats and identify "today's" content
- Content Classification: Distinguish regulations from news, guidance, etc.

Always provide structured analysis that can be used to build reliable extraction patterns for daily monitoring."""

        super().__init__(
            agent_id="publication_page_intelligence",
            agent_role=AgentRole.HTML_EXTRACTOR,
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Initialize knowledge base for learning
        if knowledge_base:
            self.knowledge_base = knowledge_base
        else:
            self.knowledge_base = JurisdictionKnowledgeBase(storage_path)
        
        # Storage setup
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Session data
        self.current_session_id = None
        self.session_start_time = None
        
    async def _register_tools(self):
        """Register publication page intelligence tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="analyze_daily_publication_page",
            function=self._analyze_daily_publication_page,
            description="Analyze a daily publication page to extract today's publications using learned patterns",
            parameters={
                "type": "object", 
                "properties": {
                    "page_url": {"type": "string", "description": "URL of the daily publication page"},
                    "source_id": {"type": "string", "description": "Source ID for learning association"},
                    "jurisdiction": {"type": "string", "description": "Jurisdiction (e.g., Spain, Germany)"},
                    "use_learning": {"type": "boolean", "description": "Whether to use learned patterns (default: true)"}
                },
                "required": ["page_url", "source_id", "jurisdiction"]
            }
        )
        
        self.register_tool(
            name="extract_publication_patterns",
            function=self._extract_publication_patterns,
            description="Extract and learn new patterns from a publication page",
            parameters={
                "type": "object",
                "properties": {
                    "page_url": {"type": "string", "description": "URL to analyze for patterns"},
                    "page_content": {"type": "string", "description": "HTML content to analyze"},
                    "source_id": {"type": "string", "description": "Source ID"},
                    "jurisdiction": {"type": "string", "description": "Jurisdiction"}
                },
                "required": ["page_url", "page_content", "source_id", "jurisdiction"]
            }
        )
        
        self.register_tool(
            name="optimize_source_patterns",
            function=self.optimize_patterns_for_source,
            description="Optimize extraction patterns for a source using reinforcement learning",
            parameters={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source identifier to optimize"},
                    "jurisdiction": {"type": "string", "description": "Jurisdiction code"},
                    "min_sessions": {"type": "number", "description": "Minimum learning sessions required (default: 5)"}
                },
                "required": ["source_id", "jurisdiction"]
            }
        )
        
        self.register_tool(
            name="get_pattern_recommendations",
            function=self._get_pattern_recommendations,
            description="Get pattern recommendations for improving extraction performance",
            parameters={
                "type": "object",
                "properties": {
                    "jurisdiction": {"type": "string", "description": "Jurisdiction to analyze"},
                    "source_id": {"type": "string", "description": "Specific source to analyze (optional)"}
                },
                "required": ["jurisdiction"]
            }
        )
    
    async def _analyze_daily_publication_page(
        self,
        page_url: str,
        source_id: str,
        jurisdiction: str,
        use_learning: bool = True
    ) -> Dict[str, Any]:
        """Analyze a daily publication page using learned patterns and LLM intelligence"""
        
        session_id = f"intelligence_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.current_session_id = session_id
        self.session_start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting intelligent page analysis: {page_url}")
            
            # Fetch page content
            page_content = await self._fetch_page_content(page_url)
            if not page_content:
                return {"success": False, "error": "Could not fetch page content"}
            
            publications = []
            extraction_method = "unknown"
            patterns_used = []
            
            # Step 1: Try learned patterns first (if available)
            if use_learning:
                learned_result = await self._try_learned_patterns(
                    page_url, page_content, source_id, jurisdiction
                )
                
                if learned_result["success"] and learned_result.get("publications"):
                    publications = learned_result["publications"]
                    extraction_method = "learned_patterns"
                    patterns_used = learned_result.get("patterns_used", [])
                    
                    self.logger.info(f"Successfully used learned patterns: found {len(publications)} publications")
                    
                    # Update pattern success
                    await self._update_pattern_success(patterns_used, len(publications))
            
            # Step 2: If learned patterns failed or unavailable, use LLM analysis
            if not publications:
                # If we tried learned patterns but got no results, mark as failure
                if patterns_used:
                    await self._update_pattern_failure(patterns_used, "no_publications_found")
                    self.logger.info(f"Learned patterns failed to find publications, falling back to LLM analysis")
                
                llm_result = await self._analyze_with_llm(
                    page_url, page_content, source_id, jurisdiction
                )
                
                if llm_result["success"]:
                    publications = llm_result.get("publications", [])
                    extraction_method = "llm_analysis"
                    
                    # Learn new patterns from successful LLM analysis
                    if publications:
                        await self._learn_from_llm_success(
                            page_url, page_content, source_id, jurisdiction, llm_result
                        )
            
            # Step 3: Record learning session
            session_end_time = datetime.utcnow()
            extraction_time = (session_end_time - self.session_start_time).total_seconds()
            
            learning_session = LearningSession(
                session_id=session_id,
                timestamp=self.session_start_time,
                source_id=source_id,
                jurisdiction=jurisdiction,
                extraction_method=extraction_method,
                patterns_used=patterns_used,
                success=len(publications) > 0,
                items_found=len(publications),
                extraction_time=extraction_time
            )
            
            if len(publications) == 0:
                learning_session.error_message = "No publications found"
                learning_session.notes.append("Consider updating patterns or LLM analysis")
            
            self.knowledge_base.record_learning_session(learning_session)
            
            return {
                "success": True,
                "page_url": page_url,
                "publications": [pub.to_dict() for pub in publications],
                "extraction_method": extraction_method,
                "patterns_used": patterns_used,
                "items_found": len(publications),
                "extraction_time": extraction_time,
                "session_id": session_id
            }
            
        except Exception as e:
            self.logger.error(f"Error in intelligent page analysis: {e}")
            
            # Record failed learning session
            if self.current_session_id:
                failed_session = LearningSession(
                    session_id=self.current_session_id,
                    timestamp=self.session_start_time or datetime.utcnow(),
                    source_id=source_id,
                    jurisdiction=jurisdiction,
                    extraction_method="failed",
                    success=False,
                    error_message=str(e)
                )
                self.knowledge_base.record_learning_session(failed_session)
            
            return {"success": False, "error": str(e)}
    
    async def optimize_patterns_for_source(self, source_id: str, jurisdiction: str, min_sessions: int = 5) -> Dict[str, Any]:
        """Optimize extraction patterns for a source using reinforcement learning principles"""
        try:
            # Get source profile
            source_profile = self.knowledge_base.get_or_create_source_profile(
                source_id=source_id,
                source_name="Unknown",
                base_url="",
                jurisdiction=jurisdiction
            )
            
            # Get recent learning sessions for this source
            recent_sessions = [
                session for session in self.knowledge_base.learning_sessions
                if session.source_id == source_id and session.success
            ]
            
            if len(recent_sessions) < min_sessions:
                return {
                    "success": False,
                    "error": f"Not enough learning sessions ({len(recent_sessions)} < {min_sessions})",
                    "recommendations": "Continue monitoring to gather more training data"
                }
            
            optimization_results = {
                "patterns_optimized": 0,
                "patterns_created": 0,
                "patterns_deprecated": 0,
                "recommendations": []
            }
            
            # Analyze pattern performance
            pattern_performance = {}
            for pattern_id, pattern in source_profile.extraction_patterns.items():
                success_rate = pattern.confidence_score
                usage_frequency = pattern.success_count + pattern.failure_count
                avg_items_found = pattern.avg_items_found
                
                pattern_performance[pattern_id] = {
                    "pattern": pattern,
                    "score": success_rate * 0.6 + (usage_frequency / 100) * 0.2 + (avg_items_found / 10) * 0.2,
                    "success_rate": success_rate,
                    "usage_frequency": usage_frequency,
                    "avg_items": avg_items_found
                }
            
            # Deprecate underperforming patterns
            for pattern_id, perf in pattern_performance.items():
                if perf["success_rate"] < 0.3 and perf["usage_frequency"] > 5:
                    del source_profile.extraction_patterns[pattern_id]
                    optimization_results["patterns_deprecated"] += 1
                    optimization_results["recommendations"].append(
                        f"Deprecated low-performing pattern: {pattern_id} (success rate: {perf['success_rate']:.2f})"
                    )
            
            # Identify successful session patterns for reinforcement
            successful_patterns = {}
            for session in recent_sessions[-10:]:  # Last 10 successful sessions
                if session.items_found > 0:
                    for pattern_id in session.patterns_used:
                        if pattern_id not in successful_patterns:
                            successful_patterns[pattern_id] = {"uses": 0, "total_items": 0}
                        successful_patterns[pattern_id]["uses"] += 1
                        successful_patterns[pattern_id]["total_items"] += session.items_found
            
            # Reinforce successful patterns
            for pattern_id, stats in successful_patterns.items():
                if pattern_id in source_profile.extraction_patterns:
                    pattern = source_profile.extraction_patterns[pattern_id]
                    # Apply reinforcement bonus
                    avg_items = stats["total_items"] / stats["uses"]
                    reinforcement_bonus = min(0.1, avg_items * 0.01)  # Cap at 0.1
                    
                    # Update pattern metrics with reinforcement
                    old_confidence = pattern.confidence_score
                    pattern.confidence_score = min(1.0, pattern.confidence_score + reinforcement_bonus)
                    pattern.avg_items_found = (pattern.avg_items_found + avg_items) / 2
                    
                    if pattern.confidence_score > old_confidence:
                        optimization_results["patterns_optimized"] += 1
                        optimization_results["recommendations"].append(
                            f"Reinforced pattern {pattern_id}: confidence {old_confidence:.3f} → {pattern.confidence_score:.3f}"
                        )
            
            # Create new patterns from highly successful sessions
            high_success_sessions = [
                session for session in recent_sessions[-5:]
                if session.items_found >= 5 and session.extraction_time < 30.0
            ]
            
            if high_success_sessions:
                # This would involve analyzing successful sessions to extract new patterns
                # For now, we'll create a placeholder pattern based on session success
                new_pattern_id = f"optimized_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                avg_success_items = sum(s.items_found for s in high_success_sessions) / len(high_success_sessions)
                
                new_pattern = ExtractionPattern(
                    pattern_id=new_pattern_id,
                    pattern_type=PatternType.PAGE_STRUCTURE,
                    pattern_value="auto_optimized_structure",
                    description=f"Auto-generated optimized pattern based on {len(high_success_sessions)} successful sessions",
                    success_count=len(high_success_sessions),
                    confidence_score=0.7,  # Start with good confidence
                    avg_items_found=avg_success_items,
                    applies_to=[source_id]
                )
                
                source_profile.add_pattern(new_pattern)
                optimization_results["patterns_created"] += 1
                optimization_results["recommendations"].append(
                    f"Created optimized pattern {new_pattern_id} based on successful session analysis"
                )
            
            # Update source profile metrics
            source_profile.overall_success_rate = sum(s.items_found > 0 for s in recent_sessions) / len(recent_sessions)
            source_profile.avg_items_per_session = sum(s.items_found for s in recent_sessions) / len(recent_sessions)
            
            # Save optimizations
            self.knowledge_base.save_knowledge_base()
            
            optimization_results["success"] = True
            optimization_results["source_id"] = source_id
            optimization_results["sessions_analyzed"] = len(recent_sessions)
            optimization_results["current_patterns"] = len(source_profile.extraction_patterns)
            optimization_results["overall_success_rate"] = source_profile.overall_success_rate
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error optimizing patterns for {source_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_pattern_recommendations(self, jurisdiction: str, source_id: str = None) -> Dict[str, Any]:
        """Get pattern recommendations for improving extraction performance"""
        try:
            recommendations = {
                "jurisdiction": jurisdiction,
                "analysis_date": datetime.utcnow().isoformat(),
                "recommendations": [],
                "optimization_opportunities": [],
                "pattern_insights": []
            }
            
            # Get jurisdiction profile
            if jurisdiction not in self.knowledge_base.jurisdiction_profiles:
                return {
                    "success": False,
                    "error": f"No learning data found for jurisdiction {jurisdiction}",
                    "recommendations": ["Start monitoring sources to generate learning data"]
                }
            
            jurisdiction_profile = self.knowledge_base.jurisdiction_profiles[jurisdiction]
            
            # Analyze sources in jurisdiction
            sources_to_analyze = []
            if source_id:
                if source_id in jurisdiction_profile.source_profiles:
                    sources_to_analyze = [jurisdiction_profile.source_profiles[source_id]]
            else:
                sources_to_analyze = list(jurisdiction_profile.source_profiles.values())
            
            for source_profile in sources_to_analyze:
                source_recommendations = []
                
                # Check if source needs more learning sessions
                if source_profile.learning_sessions < 5:
                    source_recommendations.append({
                        "priority": "high",
                        "type": "data_collection",
                        "message": f"Source {source_profile.source_id} needs more learning sessions (current: {source_profile.learning_sessions})",
                        "action": "Run more monitoring sessions"
                    })
                
                # Check pattern performance
                low_confidence_patterns = [
                    p for p in source_profile.extraction_patterns.values()
                    if p.confidence_score < 0.5
                ]
                
                if low_confidence_patterns:
                    source_recommendations.append({
                        "priority": "medium",
                        "type": "pattern_optimization",
                        "message": f"Source {source_profile.source_id} has {len(low_confidence_patterns)} low-confidence patterns",
                        "action": "Run pattern optimization or review pattern definitions"
                    })
                
                # Check for optimization opportunities
                if source_profile.learning_sessions >= 5 and source_profile.overall_success_rate < 0.7:
                    recommendations["optimization_opportunities"].append({
                        "source_id": source_profile.source_id,
                        "current_success_rate": source_profile.overall_success_rate,
                        "total_patterns": len(source_profile.extraction_patterns),
                        "recommendation": "Consider running pattern optimization - success rate below 70%"
                    })
                
                recommendations["recommendations"].extend(source_recommendations)
            
            # Add jurisdiction-wide insights
            total_patterns = sum(
                len(sp.extraction_patterns) for sp in jurisdiction_profile.source_profiles.values()
            )
            
            recommendations["pattern_insights"].append({
                "metric": "total_patterns",
                "value": total_patterns,
                "insight": f"Jurisdiction has {total_patterns} learned patterns across {len(jurisdiction_profile.source_profiles)} sources"
            })
            
            recommendations["pattern_insights"].append({
                "metric": "avg_success_rate",
                "value": jurisdiction_profile.avg_success_rate,
                "insight": f"Average success rate: {jurisdiction_profile.avg_success_rate:.2%}"
            })
            
            return {"success": True, **recommendations}
            
        except Exception as e:
            self.logger.error(f"Error getting pattern recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch page content with proper headers"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                self.logger.warning(f"HTTP {response.status_code} for {url}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def _try_learned_patterns(
        self,
        page_url: str,
        page_content: str,
        source_id: str,
        jurisdiction: str
    ) -> Dict[str, Any]:
        """Try using learned patterns to extract publications"""
        
        try:
            # Get source profile with learned patterns
            source_profile = self.knowledge_base.get_or_create_source_profile(
                source_id, "", page_url, jurisdiction
            )
            
            # Get best CSS selector patterns
            css_patterns = source_profile.get_best_patterns(
                PatternType.CSS_SELECTOR, min_confidence=0.6
            )
            
            if not css_patterns:
                return {"success": False, "reason": "No learned CSS patterns available"}
            
            soup = BeautifulSoup(page_content, 'html.parser')
            publications = []
            patterns_used = []
            
            for pattern in css_patterns[:3]:  # Try top 3 patterns
                try:
                    elements = soup.select(pattern.pattern_value)
                    patterns_used.append(pattern.pattern_id)
                    
                    for element in elements[:20]:  # Limit to avoid overload
                        # Extract publication info from element
                        title = element.get_text(strip=True)
                        url = element.get('href') or element.find('a', href=True)
                        
                        if url and hasattr(url, 'get'):
                            url = url.get('href')
                        
                        if title and url:
                            # Make URL absolute
                            if url.startswith('/'):
                                from urllib.parse import urljoin
                                url = urljoin(page_url, url)
                            
                            pub = PublicationItem(
                                title=title,
                                url=url,
                                source_id=source_id,
                                extraction_method=f"learned_css_{pattern.pattern_id}",
                                confidence_score=pattern.confidence_score
                            )
                            publications.append(pub)
                    
                    if publications:
                        # Found publications with this pattern
                        break
                        
                except Exception as e:
                    self.logger.debug(f"Pattern {pattern.pattern_id} failed: {e}")
                    continue
            
            return {
                "success": len(publications) > 0,
                "publications": publications,
                "patterns_used": patterns_used,
                "method": "learned_patterns"
            }
            
        except Exception as e:
            self.logger.error(f"Error trying learned patterns: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_with_llm(
        self,
        page_url: str,
        page_content: str,
        source_id: str,
        jurisdiction: str
    ) -> Dict[str, Any]:
        """Use LLM to analyze page and extract publications"""
        
        try:
            # Truncate content for LLM analysis
            content_sample = page_content[:12000] if len(page_content) > 12000 else page_content
            
            analysis_prompt = f"""Analyze this daily publication page from {jurisdiction} to extract TODAY's regulatory publications.

PAGE URL: {page_url}
JURISDICTION: {jurisdiction}
SOURCE ID: {source_id}

HTML CONTENT:
{content_sample}

Your task:
1. Find sections containing today's/recent publications
2. Extract publication items (title, link, date if available)
3. Identify CSS selectors that could be reused for future extraction
4. Focus on NEW publications, not archives

Return JSON:
{{
    "publications_found": [
        {{
            "title": "publication title",
            "url": "full URL to publication", 
            "published_date": "date if found",
            "content_snippet": "brief description",
            "confidence": 0.0-1.0
        }}
    ],
    "extraction_patterns": [
        {{
            "type": "css_selector",
            "pattern": ".publication-item a",
            "description": "Links to daily publications",
            "confidence": 0.0-1.0
        }}
    ],
    "page_analysis": {{
        "has_daily_section": true/false,
        "date_format": "format used for dates",
        "publication_indicators": ["phrases that indicate new publications"],
        "page_structure": "description of how publications are organized"
    }}
}}

IMPORTANT: Only extract items that appear to be from today or very recent. Ignore archive sections."""
            
            response = await self.generate_response(analysis_prompt, use_tools=False)
            
            if not response or not response.get('content'):
                return {"success": False, "error": "No response from LLM"}
            
            # Parse LLM response
            content = response['content'].strip()
            
            # Handle markdown code blocks
            if content.startswith('```json'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]).strip()
            elif content.startswith('```'):
                lines = content.split('\n') 
                content = '\n'.join(lines[1:-1]).strip()
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return {"success": False, "error": "Could not find JSON in LLM response"}
            
            analysis_data = json.loads(json_match.group())
            
            # Convert to PublicationItem objects
            publications = []
            for pub_data in analysis_data.get('publications_found', []):
                pub = PublicationItem(
                    title=pub_data.get('title', ''),
                    url=pub_data.get('url', ''),
                    content_snippet=pub_data.get('content_snippet', ''),
                    confidence_score=pub_data.get('confidence', 0.5),
                    source_id=source_id,
                    extraction_method="llm_analysis"
                )
                
                # Parse date if provided
                if pub_data.get('published_date'):
                    try:
                        pub.published_date = datetime.fromisoformat(pub_data['published_date'])
                    except:
                        pass
                
                publications.append(pub)
            
            return {
                "success": True,
                "publications": publications,
                "analysis_data": analysis_data,
                "method": "llm_analysis"
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM JSON response: {e}")
            return {"success": False, "error": f"JSON parsing error: {e}"}
        except Exception as e:
            self.logger.error(f"Error in LLM analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def _learn_from_llm_success(
        self,
        page_url: str,
        page_content: str,
        source_id: str,
        jurisdiction: str,
        llm_result: Dict[str, Any]
    ):
        """Learn new patterns from successful LLM analysis"""
        
        try:
            analysis_data = llm_result.get('analysis_data', {})
            publications = llm_result.get('publications', [])
            
            if not publications:
                return
            
            # Get or create source profile
            source_profile = self.knowledge_base.get_or_create_source_profile(
                source_id, "", page_url, jurisdiction
            )
            
            # Learn CSS selector patterns
            for pattern_data in analysis_data.get('extraction_patterns', []):
                if pattern_data.get('type') == 'css_selector':
                    pattern_id = hashlib.md5(
                        f"{source_id}_{pattern_data.get('pattern', '')}".encode()
                    ).hexdigest()[:12]
                    
                    pattern = ExtractionPattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.CSS_SELECTOR,
                        pattern_value=pattern_data.get('pattern', ''),
                        description=pattern_data.get('description', ''),
                        confidence_score=pattern_data.get('confidence', 0.7),
                        applies_to=[page_url]
                    )
                    
                    # Mark as immediately successful
                    pattern.update_success(items_found=len(publications), extraction_time=0.0)
                    
                    source_profile.add_pattern(pattern)
                    self.logger.info(f"Learned new CSS pattern: {pattern.pattern_value}")
            
            # Update source profile metrics
            extraction_time = (datetime.utcnow() - self.session_start_time).total_seconds()
            source_profile.update_success_metrics(len(publications), extraction_time)
            
            # Learn common jurisdiction patterns
            page_analysis = analysis_data.get('page_analysis', {})
            jurisdiction_profile = self.knowledge_base.get_or_create_jurisdiction(jurisdiction)
            
            # Add date formats
            date_format = page_analysis.get('date_format')
            if date_format and date_format not in jurisdiction_profile.common_date_formats:
                jurisdiction_profile.common_date_formats.append(date_format)
            
            # Add publication indicators
            indicators = page_analysis.get('publication_indicators', [])
            for indicator in indicators:
                if indicator not in jurisdiction_profile.common_content_patterns:
                    jurisdiction_profile.common_content_patterns.append(indicator)
            
            # Save knowledge base
            self.knowledge_base.save_knowledge_base()
            
            self.logger.info(f"Successfully learned patterns from LLM analysis for {source_id}")
            
        except Exception as e:
            self.logger.error(f"Error learning from LLM success: {e}")
    
    async def _update_pattern_success(self, pattern_ids: List[str], items_found: int, extraction_time: float = 0.0):
        """Update success metrics for used patterns with reinforcement learning"""
        
        try:
            current_time = datetime.utcnow()
            
            for jurisdiction in self.knowledge_base.jurisdiction_profiles.values():
                for source in jurisdiction.source_profiles.values():
                    for pattern_id in pattern_ids:
                        if pattern_id in source.extraction_patterns:
                            pattern = source.extraction_patterns[pattern_id]
                            old_confidence = pattern.confidence_score
                            
                            # Enhanced reinforcement learning update
                            pattern.update_success(items_found=items_found, extraction_time=extraction_time)
                            
                            # Apply contextual bonuses for exceptional performance
                            if items_found > 0:
                                # High item count bonus
                                if items_found >= 10:
                                    bonus = min(0.05, items_found * 0.003)
                                    pattern.confidence_score = min(1.0, pattern.confidence_score + bonus)
                                
                                # Speed bonus for fast extraction
                                if extraction_time > 0 and extraction_time < 10.0:
                                    speed_bonus = (10.0 - extraction_time) / 100.0
                                    pattern.confidence_score = min(1.0, pattern.confidence_score + speed_bonus)
                                
                                # Consistency bonus for patterns used recently
                                if pattern.last_used:
                                    hours_since = (current_time - pattern.last_used).total_seconds() / 3600
                                    if hours_since < 24:  # Used within 24 hours
                                        consistency_bonus = 0.01
                                        pattern.confidence_score = min(1.0, pattern.confidence_score + consistency_bonus)
                            
                            self.logger.debug(
                                f"Reinforcement learning update for pattern {pattern_id}: "
                                f"confidence {old_confidence:.3f} → {pattern.confidence_score:.3f}, "
                                f"items: {items_found}, time: {extraction_time:.1f}s"
                            )
                    
                    # Update source-level success metrics
                    source.update_success_metrics(items_found, extraction_time)
            
            self.knowledge_base.save_knowledge_base()
            
        except Exception as e:
            self.logger.error(f"Error updating pattern success: {e}")
    
    async def _update_pattern_failure(self, pattern_ids: List[str], error_type: str = ""):
        """Update failure metrics for patterns with penalty"""
        
        try:
            for jurisdiction in self.knowledge_base.jurisdiction_profiles.values():
                for source in jurisdiction.source_profiles.values():
                    for pattern_id in pattern_ids:
                        if pattern_id in source.extraction_patterns:
                            pattern = source.extraction_patterns[pattern_id]
                            old_confidence = pattern.confidence_score
                            
                            # Apply failure penalty
                            pattern.update_failure(error_type)
                            
                            # Additional penalty for repeated failures
                            total_attempts = pattern.success_count + pattern.failure_count
                            if total_attempts >= 5:  # Enough data to be confident
                                recent_failure_rate = pattern.failure_count / total_attempts
                                if recent_failure_rate > 0.5:  # More than 50% failure rate
                                    penalty = min(0.1, recent_failure_rate * 0.1)
                                    pattern.confidence_score = max(0.0, pattern.confidence_score - penalty)
                            
                            self.logger.debug(
                                f"Pattern failure penalty for {pattern_id}: "
                                f"confidence {old_confidence:.3f} → {pattern.confidence_score:.3f}, "
                                f"error: {error_type}"
                            )
            
            self.knowledge_base.save_knowledge_base()
            
        except Exception as e:
            self.logger.error(f"Error updating pattern failure: {e}")
    
    def get_learning_statistics(self, jurisdiction: str = None) -> Dict[str, Any]:
        """Get learning statistics for monitoring system intelligence"""
        
        stats = {
            "total_jurisdictions": len(self.knowledge_base.jurisdiction_profiles),
            "total_sources": sum(len(j.source_profiles) for j in self.knowledge_base.jurisdiction_profiles.values()),
            "total_patterns": sum(
                len(s.extraction_patterns) 
                for j in self.knowledge_base.jurisdiction_profiles.values()
                for s in j.source_profiles.values()
            ),
            "total_learning_sessions": len(self.knowledge_base.learning_sessions),
            "jurisdictions": {}
        }
        
        for code, jurisdiction in self.knowledge_base.jurisdiction_profiles.items():
            if jurisdiction is None or code == jurisdiction:
                jurisdiction_stats = {
                    "sources": len(jurisdiction.source_profiles),
                    "avg_success_rate": jurisdiction.avg_success_rate,
                    "total_patterns": sum(len(s.extraction_patterns) for s in jurisdiction.source_profiles.values()),
                    "high_confidence_patterns": sum(
                        len([p for p in s.extraction_patterns.values() if p.confidence_score >= 0.8])
                        for s in jurisdiction.source_profiles.values()
                    )
                }
                stats["jurisdictions"][code] = jurisdiction_stats
        
        return stats