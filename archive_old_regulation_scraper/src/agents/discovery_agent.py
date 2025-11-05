"""
Discovery Agent
Analyzes websites to determine optimal extraction strategies and create site profiles
"""
import asyncio
import logging
import aiohttp
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, robotparser
from urllib.robotparser import RobotFileParser
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass

from ..infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ..models.extraction_models import (
    WebsiteProfile, ExtractionJob, ExtractionStatus, 
    ContentType, ExtractionMethod
)
from ..models.regulation_models import DocumentType, Jurisdiction
from ..config.config_manager import get_config


@dataclass
class DiscoveryResult:
    """Result of website discovery analysis"""
    profile: WebsiteProfile
    recommended_methods: List[ExtractionMethod]
    estimated_documents: int
    confidence: float
    analysis_time: float


class WebsiteAnalyzer:
    """Analyzes website structure and content"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    async def analyze_homepage(self, url: str) -> Dict[str, Any]:
        """Analyze website homepage"""
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}"}
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                return {
                    "title": soup.title.string if soup.title else None,
                    "content": content,
                    "soup": soup,
                    "response_headers": dict(response.headers),
                    "final_url": str(response.url)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to analyze homepage {url}: {e}")
            return {"error": str(e)}
    
    def detect_semantic_markup(self, soup: BeautifulSoup) -> bool:
        """Detect semantic HTML markup"""
        semantic_tags = [
            'article', 'section', 'nav', 'header', 'footer', 'aside',
            'main', 'figure', 'figcaption', 'time', 'mark'
        ]
        
        semantic_count = sum(1 for tag in semantic_tags if soup.find(tag))
        return semantic_count >= 3
    
    def detect_js_dependency(self, content: str, soup: BeautifulSoup) -> bool:
        """Detect if site heavily depends on JavaScript"""
        # Check for SPA frameworks
        spa_indicators = [
            'react', 'angular', 'vue', 'ember', 'backbone',
            'ng-app', 'data-reactroot', 'v-app'
        ]
        
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in spa_indicators):
            return True
        
        # Check script to content ratio
        scripts = soup.find_all('script')
        script_content = ''.join(script.get_text() for script in scripts if script.string)
        
        if len(script_content) > len(soup.get_text()) * 0.5:
            return True
        
        # Check for dynamic content indicators
        dynamic_indicators = [
            'loading', 'spinner', 'data-', 'ng-', 'v-', 'x-data'
        ]
        
        for indicator in dynamic_indicators:
            if soup.find(attrs={'class': re.compile(indicator, re.I)}):
                return True
        
        return False
    
    def analyze_content_types(self, soup: BeautifulSoup) -> Dict[ContentType, float]:
        """Analyze distribution of content types"""
        content_analysis = {
            ContentType.TEXT: 0.0,
            ContentType.TABLE: 0.0,
            ContentType.LIST: 0.0,
            ContentType.FORM: 0.0,
            ContentType.IMAGE: 0.0
        }
        
        # Count elements
        text_elements = len(soup.find_all(['p', 'div', 'span', 'article']))
        table_elements = len(soup.find_all('table'))
        list_elements = len(soup.find_all(['ul', 'ol', 'dl']))
        form_elements = len(soup.find_all('form'))
        image_elements = len(soup.find_all(['img', 'figure']))
        
        total = max(1, text_elements + table_elements + list_elements + form_elements + image_elements)
        
        content_analysis[ContentType.TEXT] = text_elements / total
        content_analysis[ContentType.TABLE] = table_elements / total
        content_analysis[ContentType.LIST] = list_elements / total
        content_analysis[ContentType.FORM] = form_elements / total
        content_analysis[ContentType.IMAGE] = image_elements / total
        
        return content_analysis
    
    def detect_complex_tables(self, soup: BeautifulSoup) -> bool:
        """Detect complex table structures"""
        tables = soup.find_all('table')
        
        for table in tables:
            # Check for nested tables
            if table.find('table'):
                return True
            
            # Check for complex structures
            if (table.find('thead') and table.find('tbody')) or \
               len(table.find_all('th')) > 5 or \
               len(table.find_all('tr')) > 10:
                return True
        
        return False
    
    def detect_language(self, soup: BeautifulSoup) -> str:
        """Detect primary language"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            lang = html_tag['lang'].split('-')[0].lower()
            return lang
        
        # Check meta tags
        meta_lang = soup.find('meta', {'name': 'language'}) or \
                   soup.find('meta', {'http-equiv': 'content-language'})
        
        if meta_lang and meta_lang.get('content'):
            lang = meta_lang['content'].split('-')[0].lower()
            return lang
        
        # Default to English
        return 'en'
    
    def estimate_documents(self, soup: BeautifulSoup, url: str) -> int:
        """Estimate number of documents available"""
        # Look for pagination indicators
        pagination_selectors = [
            'pagination', 'pager', 'page-numbers', 'next', 'previous'
        ]
        
        pagination_count = 0
        for selector in pagination_selectors:
            elements = soup.find_all(class_=re.compile(selector, re.I))
            pagination_count += len(elements)
        
        # Look for document links
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx)$', re.I))
        direct_docs = len(doc_links)
        
        # Look for list items that might be documents
        list_items = soup.find_all('li')
        potential_docs = len([li for li in list_items if li.find('a')])
        
        # Estimate based on indicators
        if pagination_count > 5:
            estimated = potential_docs * (pagination_count // 2)
        elif direct_docs > 0:
            estimated = direct_docs * 2  # Assume more docs not immediately visible
        else:
            estimated = max(10, potential_docs // 3)  # Conservative estimate
        
        return min(10000, estimated)  # Cap at reasonable maximum


class RobotsAnalyzer:
    """Analyzes robots.txt for crawling permissions"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    async def check_robots_txt(self, url: str, user_agent: str = "*") -> Dict[str, Any]:
        """Check robots.txt for crawling permissions"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            async with self.session.get(robots_url, timeout=10) as response:
                if response.status != 200:
                    return {"allowed": True, "reason": "No robots.txt found"}
                
                robots_content = await response.text()
                
                # Parse robots.txt
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                
                # Check if crawling is allowed
                allowed = rp.can_fetch(user_agent, url)
                
                # Get crawl delay
                crawl_delay = rp.crawl_delay(user_agent)
                
                return {
                    "allowed": allowed,
                    "crawl_delay": crawl_delay,
                    "robots_content": robots_content,
                    "sitemap": rp.site_maps() if hasattr(rp, 'site_maps') else None
                }
                
        except Exception as e:
            self.logger.warning(f"Failed to check robots.txt for {url}: {e}")
            return {"allowed": True, "reason": f"Error checking robots.txt: {e}"}


class JurisdictionDetector:
    """Detects legal jurisdiction and document types"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Domain patterns for different jurisdictions
        self.domain_patterns = {
            Jurisdiction.UK: [
                r'\.gov\.uk$', r'\.parliament\.uk$', r'\.legislation\.gov\.uk$'
            ],
            Jurisdiction.EU: [
                r'\.europa\.eu$', r'\.eur-lex\.europa\.eu$', r'\.ec\.europa\.eu$'
            ],
            Jurisdiction.US: [
                r'\.gov$', r'\.senate\.gov$', r'\.house\.gov$', r'\.congress\.gov$'
            ],
            Jurisdiction.CANADA: [
                r'\.gc\.ca$', r'\.parl\.gc\.ca$', r'\.justice\.gc\.ca$'
            ],
            Jurisdiction.AUSTRALIA: [
                r'\.gov\.au$', r'\.aph\.gov\.au$', r'\.ag\.gov\.au$'
            ]
        }
        
        # Content keywords for document types
        self.document_keywords = {
            DocumentType.LEGISLATION: [
                'legislation', 'law', 'statute', 'code', 'legal'
            ],
            DocumentType.REGULATION: [
                'regulation', 'rule', 'regulatory', 'compliance'
            ],
            DocumentType.BILL: [
                'bill', 'proposed', 'draft', 'house bill', 'senate bill'
            ],
            DocumentType.ACT: [
                'act', 'public law', 'enacted'
            ],
            DocumentType.DIRECTIVE: [
                'directive', 'instruction', 'guideline'
            ]
        }
    
    def detect_jurisdiction(self, url: str, content: str) -> Optional[Jurisdiction]:
        """Detect jurisdiction based on URL and content"""
        domain = urlparse(url).netloc.lower()
        
        # Check domain patterns
        for jurisdiction, patterns in self.domain_patterns.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    return jurisdiction
        
        # Check content for jurisdiction indicators
        content_lower = content.lower()
        
        jurisdiction_keywords = {
            Jurisdiction.UK: ['united kingdom', 'uk government', 'parliament uk'],
            Jurisdiction.EU: ['european union', 'european commission', 'eur-lex'],
            Jurisdiction.US: ['united states', 'us government', 'congress'],
            Jurisdiction.CANADA: ['government of canada', 'canada.gc.ca'],
            Jurisdiction.AUSTRALIA: ['australian government', 'australia.gov.au']
        }
        
        jurisdiction_scores = {}
        for jurisdiction, keywords in jurisdiction_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                jurisdiction_scores[jurisdiction] = score
        
        if jurisdiction_scores:
            return max(jurisdiction_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def detect_document_types(self, content: str) -> List[DocumentType]:
        """Detect document types based on content"""
        content_lower = content.lower()
        detected_types = []
        
        for doc_type, keywords in self.document_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_types.append(doc_type)
        
        return detected_types or [DocumentType.OTHER]


class DiscoveryAgent:
    """Main discovery agent for website analysis"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.session: Optional[aiohttp.ClientSession] = None
        self.website_analyzer: Optional[WebsiteAnalyzer] = None
        self.robots_analyzer: Optional[RobotsAnalyzer] = None
        self.jurisdiction_detector = JurisdictionDetector()
        
        # Agent configuration
        self.agent_config = self.config.agents.get('discovery', self.config.agents.get('default'))
        
        # Cache for profiles
        self.profile_cache: Dict[str, WebsiteProfile] = {}
        self.cache_ttl = timedelta(hours=24)
        
    async def start(self):
        """Start the discovery agent"""
        self.logger.info("Starting Discovery Agent")
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.agent_config.timeout)
        headers = {'User-Agent': self.agent_config.user_agent}
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        )
        
        # Initialize analyzers
        self.website_analyzer = WebsiteAnalyzer(self.session)
        self.robots_analyzer = RobotsAnalyzer(self.session)
        
        # Subscribe to relevant message types
        await self.broker.subscribe_queue("discovery", self._handle_message)
        
        # Start listening for messages
        await self.broker.start_queue_listener("discovery")
    
    async def stop(self):
        """Stop the discovery agent"""
        self.logger.info("Stopping Discovery Agent")
        
        if self.session:
            await self.session.close()
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages"""
        try:
            if message.type == MessageType.JOB_CREATED:
                await self._handle_job_created(message)
            else:
                self.logger.debug(f"Ignoring message type: {message.type}")
                
        except Exception as e:
            self.logger.error(f"Error handling message {message.id}: {e}")
    
    async def _handle_job_created(self, message: Message):
        """Handle job creation message"""
        try:
            url = message.payload.get('url')
            job_id = message.payload.get('job_id')
            
            if not url:
                self.logger.error(f"No URL in job creation message: {message.id}")
                return
            
            self.logger.info(f"Analyzing website: {url}")
            
            # Perform discovery analysis
            start_time = time.time()
            result = await self.analyze_website(url)
            analysis_time = time.time() - start_time
            
            # Send analysis result
            response_message = await create_message(
                message_type=MessageType.WEBSITE_ANALYZED,
                sender="discovery_agent",
                recipient="orchestrator",
                payload={
                    "job_id": job_id,
                    "url": url,
                    "profile": result.profile.dict(),
                    "recommended_methods": [method.value for method in result.recommended_methods],
                    "estimated_documents": result.estimated_documents,
                    "confidence": result.confidence,
                    "analysis_time": analysis_time
                },
                correlation_id=message.correlation_id
            )
            
            await self.broker.publish(response_message)
            
        except Exception as e:
            self.logger.error(f"Error handling job creation: {e}")
            
            # Send error message
            error_message = await create_message(
                message_type=MessageType.JOB_FAILED,
                sender="discovery_agent",
                recipient="orchestrator",
                payload={
                    "job_id": message.payload.get('job_id'),
                    "url": message.payload.get('url'),
                    "error": str(e)
                },
                correlation_id=message.correlation_id
            )
            
            await self.broker.publish(error_message)
    
    async def analyze_website(self, url: str) -> DiscoveryResult:
        """Analyze a website and create profile"""
        start_time = time.time()
        
        # Check cache first
        domain = urlparse(url).netloc
        if domain in self.profile_cache:
            cached_profile = self.profile_cache[domain]
            if datetime.utcnow() - cached_profile.profiled_at < self.cache_ttl:
                self.logger.debug(f"Using cached profile for {domain}")
                return DiscoveryResult(
                    profile=cached_profile,
                    recommended_methods=self._get_recommended_methods(cached_profile),
                    estimated_documents=cached_profile.estimated_documents or 100,
                    confidence=cached_profile.confidence,
                    analysis_time=0.0
                )
        
        try:
            # Analyze robots.txt
            robots_result = await self.robots_analyzer.check_robots_txt(
                url, self.agent_config.user_agent
            )
            
            # Analyze homepage
            homepage_result = await self.website_analyzer.analyze_homepage(url)
            
            if "error" in homepage_result:
                raise Exception(f"Failed to analyze homepage: {homepage_result['error']}")
            
            soup = homepage_result["soup"]
            content = homepage_result["content"]
            
            # Create website profile
            profile = WebsiteProfile(
                domain=domain,
                base_url=url,
                title=homepage_result.get("title"),
                
                # Technical characteristics
                has_semantic_markup=self.website_analyzer.detect_semantic_markup(soup),
                js_dependent=self.website_analyzer.detect_js_dependency(content, soup),
                uses_spa=self._detect_spa(content),
                pdf_ratio=self._estimate_pdf_ratio(soup),
                has_complex_tables=self.website_analyzer.detect_complex_tables(soup),
                has_forms=bool(soup.find('form')),
                
                # Content characteristics
                content_types=self.website_analyzer.analyze_content_types(soup),
                estimated_documents=self.website_analyzer.estimate_documents(soup, url),
                
                # Language detection
                language=self.website_analyzer.detect_language(soup),
                
                # Jurisdiction and legal framework
                jurisdiction=self.jurisdiction_detector.detect_jurisdiction(url, content),
                document_types=self.jurisdiction_detector.detect_document_types(content),
                
                # Technical details
                robots_allowed=robots_result["allowed"],
                rate_limit_info={"crawl_delay": robots_result.get("crawl_delay")},
                
                # Analysis metadata
                profiled_at=datetime.utcnow(),
                confidence=self._calculate_confidence(soup, content)
            )
            
            # Cache profile
            self.profile_cache[domain] = profile
            
            # Determine recommended methods
            recommended_methods = self._get_recommended_methods(profile)
            
            analysis_time = time.time() - start_time
            
            self.logger.info(f"Website analysis completed for {domain} in {analysis_time:.2f}s")
            
            return DiscoveryResult(
                profile=profile,
                recommended_methods=recommended_methods,
                estimated_documents=profile.estimated_documents or 100,
                confidence=profile.confidence,
                analysis_time=analysis_time
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing website {url}: {e}")
            
            # Return minimal profile with error
            profile = WebsiteProfile(
                domain=domain,
                base_url=url,
                confidence=0.0,
                profiled_at=datetime.utcnow()
            )
            
            return DiscoveryResult(
                profile=profile,
                recommended_methods=[ExtractionMethod.HTML_PARSING],
                estimated_documents=50,
                confidence=0.0,
                analysis_time=time.time() - start_time
            )
    
    def _detect_spa(self, content: str) -> bool:
        """Detect Single Page Application"""
        spa_indicators = [
            'single page application', 'spa', 'router-outlet', 
            'ui-router', 'react-router', 'vue-router'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in spa_indicators)
    
    def _estimate_pdf_ratio(self, soup: BeautifulSoup) -> float:
        """Estimate ratio of PDF content"""
        all_links = soup.find_all('a', href=True)
        pdf_links = [link for link in all_links if link['href'].lower().endswith('.pdf')]
        
        if not all_links:
            return 0.0
        
        return len(pdf_links) / len(all_links)
    
    def _calculate_confidence(self, soup: BeautifulSoup, content: str) -> float:
        """Calculate confidence in the analysis"""
        confidence_factors = []
        
        # Factor 1: Content richness
        text_length = len(soup.get_text())
        if text_length > 10000:
            confidence_factors.append(0.9)
        elif text_length > 1000:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        # Factor 2: Structure quality
        if soup.find('title') and soup.find('nav'):
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # Factor 3: Semantic markup
        semantic_score = 0.8 if self.website_analyzer.detect_semantic_markup(soup) else 0.6
        confidence_factors.append(semantic_score)
        
        # Factor 4: Legal content indicators
        legal_keywords = ['law', 'regulation', 'act', 'bill', 'legal', 'statute']
        legal_score = 0.9 if any(kw in content.lower() for kw in legal_keywords) else 0.5
        confidence_factors.append(legal_score)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _get_recommended_methods(self, profile: WebsiteProfile) -> List[ExtractionMethod]:
        """Get recommended extraction methods based on profile"""
        methods = []
        
        # Always include HTML parsing as base method
        methods.append(ExtractionMethod.HTML_PARSING)
        
        # Add PDF extraction if significant PDF content
        if profile.pdf_ratio > 0.1:
            methods.append(ExtractionMethod.PDF_EXTRACTION)
        
        # Add OCR for image-heavy content or poor accessibility
        if (profile.content_types.get(ContentType.IMAGE, 0) > 0.2 or 
            profile.accessibility_score < 0.5):
            methods.append(ExtractionMethod.OCR)
        
        # Add computer vision for complex layouts
        if profile.has_complex_tables:
            methods.append(ExtractionMethod.COMPUTER_VISION)
        
        # Use hybrid approach for complex sites
        if profile.js_dependent or profile.uses_spa:
            if ExtractionMethod.HYBRID not in methods:
                methods.append(ExtractionMethod.HYBRID)
        
        return methods