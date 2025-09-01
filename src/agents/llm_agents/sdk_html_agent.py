"""
SDK-Based HTML Extraction Agent
Modern OpenAI Agents SDK implementation for HTML content extraction and DOM processing
"""
import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString, Tag
import re
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

from agents.tools import function_tool
from .sdk_base_agent import BaseSDKAgent, SDKAgentContext
from .base_agent import AgentRole
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractedContent, ContentType
from ...models.regulation_models import Regulation, DocumentType


# Pydantic models for structured extraction
class ExtractedDocument(BaseModel):
    """Structured document extraction result"""
    title: str
    content: str
    document_type: str
    url: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    word_count: int = 0
    language: Optional[str] = None


class ExtractionSummary(BaseModel):
    """Summary of extraction results"""
    total_documents: int
    successful_extractions: int
    failed_extractions: int
    average_confidence: float = Field(ge=0.0, le=1.0)
    extraction_methods_used: List[str]
    challenges_encountered: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SDKHTMLExtractionAgent(BaseSDKAgent):
    """SDK-powered HTML Extraction Agent for DOM processing"""
    
    def __init__(self, broker):
        instructions = """You are an expert HTML Content Extraction Agent specialized in extracting structured legal and regulatory content from web pages using advanced DOM analysis.

Your core capabilities:
1. Intelligent HTML parsing and content extraction from complex web structures
2. JavaScript-heavy website handling using browser automation
3. Multi-page navigation and content aggregation
4. Content quality assessment and filtering
5. Structured data extraction with metadata preservation
6. Adaptive extraction strategies based on website patterns

Available extraction tools:
- Static HTML parsing for simple sites with BeautifulSoup
- Dynamic browser automation for JavaScript-heavy sites using Playwright  
- Multi-page extraction with intelligent pagination handling
- Content quality assessment and confidence scoring
- Metadata extraction including document types, dates, and classifications
- Link following for comprehensive content discovery

Your extraction process:
1. Analyze the provided URLs and extraction strategy from Discovery analysis
2. Choose optimal extraction method (static parsing vs browser automation)
3. Extract content systematically with quality assessment
4. Handle pagination and multi-page documents intelligently
5. Clean and structure extracted content for downstream processing
6. Provide confidence scores and recommendations for validation

Content quality standards:
- Extract complete document text with proper formatting
- Preserve document structure (headings, sections, lists)
- Capture metadata (titles, dates, document numbers, classifications)
- Filter out navigation, ads, and irrelevant content
- Maintain content traceability with source URLs
- Score extraction confidence based on completeness and accuracy"""

        super().__init__(
            agent_id="sdk_html_extraction_agent",
            agent_role=AgentRole.HTML_EXTRACTOR,
            broker=broker,
            instructions=instructions,
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # HTTP session for static extraction
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Browser context for dynamic extraction  
        self.playwright = None
        self.browser = None
        
        # Extraction cache and state
        self.extraction_cache: Dict[str, Dict[str, Any]] = {}
        self.active_extractions: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start HTML extraction agent with both static and dynamic capabilities"""
        # Initialize HTTP session
        timeout = aiohttp.ClientTimeout(total=60)  # Longer timeout for complex pages
        headers = {
            'User-Agent': 'RegulationScraper-HTMLExtractor-SDK/2.0 (Legal Content Extraction)'
        }
        
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        
        # Initialize Playwright for dynamic content
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        await super().start()
        self.logger.info("HTML Extraction Agent started with static and dynamic capabilities")
    
    async def stop(self):
        """Stop extraction agent and cleanup resources"""
        if self.session:
            await self.session.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        await super().stop()
    
    async def _register_tools(self):
        """Register HTML extraction tools"""
        
        self.register_function_tool(
            self._extract_static_html,
            name="extract_static_html",
            description="Extract content from HTML pages using static parsing with BeautifulSoup"
        )
        
        self.register_function_tool(
            self._extract_dynamic_html,
            name="extract_dynamic_html", 
            description="Extract content from JavaScript-heavy pages using browser automation"
        )
        
        self.register_function_tool(
            self._extract_multi_page_content,
            name="extract_multi_page_content",
            description="Extract content across multiple pages with pagination handling"
        )
        
        self.register_function_tool(
            self._assess_content_quality,
            name="assess_content_quality",
            description="Assess the quality and completeness of extracted content"
        )
        
        self.register_function_tool(
            self._extract_document_metadata,
            name="extract_document_metadata",
            description="Extract metadata from documents including titles, dates, and classifications"
        )
        
        self.register_function_tool(
            self._follow_document_links,
            name="follow_document_links",
            description="Follow document links to extract content from linked pages or files"
        )
    
    async def _handle_job_request(self, message, context: SDKAgentContext):
        """Handle HTML extraction job requests"""
        job_id = message.payload.get('job_id')
        extraction_data = message.payload.get('extraction_data', {})
        url = extraction_data.get('url')
        strategy = extraction_data.get('strategy', {})
        
        if not url:
            await self._send_error_response(message, "No URL provided for HTML extraction")
            return
        
        self.logger.info(f"Starting SDK HTML extraction for job {job_id}: {url}")
        
        try:
            # Store extraction context
            extraction_context = {
                "job_id": job_id,
                "url": url,
                "strategy": strategy,
                "start_time": datetime.utcnow(),
                "status": "extracting"
            }
            self.active_extractions[job_id] = extraction_context
            
            # Create extraction prompt based on strategy
            extraction_prompt = f"""HTML content extraction request for job {job_id}:

Target URL: {url}
Extraction Strategy: {json.dumps(strategy, indent=2)}

Please perform comprehensive HTML extraction:

1. Analyze the extraction strategy to determine optimal approach (static vs dynamic)
2. Extract content systematically using the most appropriate method
3. If multiple pages are indicated, handle pagination intelligently
4. Assess content quality and provide confidence scores
5. Extract metadata for proper document classification
6. Follow relevant document links if specified in strategy

Focus on extracting complete, structured regulatory content while filtering out irrelevant material.
Provide detailed extraction summary with recommendations."""

            # Execute extraction with full tool access
            result = await self.run_agent(
                user_message=extraction_prompt,
                context=context,
                use_session=True
            )
            
            # Process extraction results
            extraction_summary = await self._create_extraction_summary(job_id, result, context)
            
            # Send results to orchestrator
            await self._send_response(
                message_type=MessageType.CONTENT_EXTRACTED,
                recipient="orchestrator", 
                payload={
                    "job_id": job_id,
                    "agent_id": self.agent_id,
                    "results": extraction_summary,
                    "execution_time": result.get("execution_time"),
                    "session_id": result.get("session_id")
                },
                correlation_id=message.correlation_id
            )
            
            # Update status
            extraction_context["status"] = "completed"
            self.logger.info(f"Completed HTML extraction for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"HTML extraction failed for job {job_id}: {e}")
            await self._send_error_response(message, str(e))
            if job_id in self.active_extractions:
                self.active_extractions[job_id]["status"] = "failed"
    
    # SDK Tool implementations
    
    async def _extract_static_html(self, url: str, selectors: Dict[str, str] = None) -> Dict[str, Any]:
        """SDK Tool: Extract content using static HTML parsing"""
        try:
            selectors = selectors or {}
            
            # Fetch HTML content
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {response.reason}"
                    }
                
                html_content = await response.text()
                final_url = str(response.url)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content using selectors or intelligent defaults
            extraction_result = {
                "success": True,
                "url": final_url,
                "title": self._extract_page_title(soup),
                "main_content": self._extract_main_content(soup, selectors),
                "metadata": self._extract_basic_metadata(soup),
                "document_links": self._extract_document_links(soup, final_url),
                "content_statistics": self._analyze_content_statistics(soup),
                "extraction_method": "static_html"
            }
            
            # Calculate confidence score
            extraction_result["confidence_score"] = self._calculate_static_confidence(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Error in static HTML extraction for {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_dynamic_html(self, url: str, wait_selectors: List[str] = None,
                                   javascript_timeout: int = 30) -> Dict[str, Any]:
        """SDK Tool: Extract content using browser automation"""
        try:
            wait_selectors = wait_selectors or []
            
            # Create new browser context for isolation
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='RegulationScraper-HTMLExtractor-SDK/2.0 (Legal Content Extraction)'
            )
            
            page = await context.new_page()
            
            try:
                # Navigate to page with timeout
                await page.goto(url, wait_until='networkidle', timeout=javascript_timeout * 1000)
                
                # Wait for specific selectors if provided
                for selector in wait_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                    except Exception as e:
                        self.logger.warning(f"Selector {selector} not found: {e}")
                
                # Get page content after JavaScript execution
                html_content = await page.content()
                final_url = page.url
                
                # Parse the dynamically loaded content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                extraction_result = {
                    "success": True,
                    "url": final_url,
                    "title": await page.title(),
                    "main_content": self._extract_main_content(soup),
                    "dynamic_elements": await self._extract_dynamic_elements(page),
                    "metadata": self._extract_basic_metadata(soup),
                    "javascript_rendered": True,
                    "content_statistics": self._analyze_content_statistics(soup),
                    "extraction_method": "dynamic_html"
                }
                
                # Calculate confidence score for dynamic content
                extraction_result["confidence_score"] = self._calculate_dynamic_confidence(extraction_result)
                
                return extraction_result
                
            finally:
                await context.close()
                
        except Exception as e:
            self.logger.error(f"Error in dynamic HTML extraction for {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_multi_page_content(self, base_url: str, pagination_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """SDK Tool: Extract content across multiple pages"""
        try:
            pagination_config = pagination_config or {}
            max_pages = pagination_config.get("max_pages", 10)
            pagination_selector = pagination_config.get("next_selector", "a[href*='next'], a[href*='page']")
            
            extracted_pages = []
            current_url = base_url
            page_count = 0
            
            while current_url and page_count < max_pages:
                page_count += 1
                self.logger.debug(f"Extracting page {page_count}: {current_url}")
                
                # Extract current page
                page_result = await self._extract_static_html(current_url)
                
                if not page_result.get("success", False):
                    self.logger.warning(f"Failed to extract page {page_count}: {current_url}")
                    break
                
                extracted_pages.append({
                    "page_number": page_count,
                    "url": current_url,
                    "content": page_result.get("main_content", ""),
                    "title": page_result.get("title", ""),
                    "metadata": page_result.get("metadata", {}),
                    "confidence_score": page_result.get("confidence_score", 0.0)
                })
                
                # Find next page URL
                current_url = await self._find_next_page_url(current_url, pagination_selector)
                
                # Prevent infinite loops
                if any(page["url"] == current_url for page in extracted_pages):
                    self.logger.warning("Detected pagination loop, stopping extraction")
                    break
                
                # Add delay to be respectful
                await asyncio.sleep(1)
            
            # Consolidate multi-page content
            consolidated_content = self._consolidate_multi_page_content(extracted_pages)
            
            return {
                "success": True,
                "base_url": base_url,
                "pages_extracted": len(extracted_pages),
                "consolidated_content": consolidated_content,
                "page_details": extracted_pages,
                "extraction_method": "multi_page",
                "average_confidence": sum(p["confidence_score"] for p in extracted_pages) / len(extracted_pages) if extracted_pages else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error in multi-page extraction for {base_url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _assess_content_quality(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """SDK Tool: Assess content quality and completeness"""
        try:
            metadata = metadata or {}
            
            quality_metrics = {
                "word_count": len(content.split()),
                "character_count": len(content),
                "paragraph_count": len(content.split('\n\n')),
                "has_title": bool(metadata.get("title")),
                "has_date": bool(metadata.get("date")),
                "has_document_number": bool(metadata.get("document_number")),
                "structural_completeness": 0.0,
                "content_coherence": 0.0,
                "legal_content_indicators": 0
            }
            
            # Assess structural completeness
            structure_score = 0.0
            if quality_metrics["word_count"] > 100:
                structure_score += 0.3
            if quality_metrics["paragraph_count"] > 3:
                structure_score += 0.2
            if content.count('\n') > 5:  # Multiple lines
                structure_score += 0.2
            if any(marker in content.lower() for marker in ['section', 'article', 'chapter']):
                structure_score += 0.3
            quality_metrics["structural_completeness"] = min(structure_score, 1.0)
            
            # Assess legal content indicators
            legal_keywords = ['regulation', 'act', 'law', 'statute', 'shall', 'whereas', 'article', 'section']
            legal_count = sum(1 for keyword in legal_keywords if keyword in content.lower())
            quality_metrics["legal_content_indicators"] = legal_count
            
            # Calculate overall quality score
            overall_quality = 0.0
            
            # Word count contribution (30%)
            if quality_metrics["word_count"] > 1000:
                overall_quality += 0.30
            elif quality_metrics["word_count"] > 500:
                overall_quality += 0.20
            elif quality_metrics["word_count"] > 100:
                overall_quality += 0.10
            
            # Structural completeness (25%)
            overall_quality += quality_metrics["structural_completeness"] * 0.25
            
            # Legal content indicators (25%)
            legal_score = min(legal_count / 10, 1.0)  # Normalize to max 10 indicators
            overall_quality += legal_score * 0.25
            
            # Metadata completeness (20%)
            metadata_score = sum([
                quality_metrics["has_title"],
                quality_metrics["has_date"], 
                quality_metrics["has_document_number"]
            ]) / 3.0
            overall_quality += metadata_score * 0.20
            
            quality_metrics["overall_quality_score"] = min(overall_quality, 1.0)
            
            # Generate quality assessment
            assessment = "high" if overall_quality >= 0.8 else "medium" if overall_quality >= 0.5 else "low"
            quality_metrics["quality_assessment"] = assessment
            
            # Provide recommendations
            recommendations = []
            if quality_metrics["word_count"] < 100:
                recommendations.append("Content appears too short - verify extraction completeness")
            if legal_count < 3:
                recommendations.append("Low legal content indicators - verify this is regulatory content")
            if not quality_metrics["has_title"]:
                recommendations.append("No title detected - may need metadata extraction improvement")
            
            quality_metrics["recommendations"] = recommendations
            
            return {
                "success": True,
                "quality_metrics": quality_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing content quality: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_document_metadata(self, html_content: str, url: str) -> Dict[str, Any]:
        """SDK Tool: Extract comprehensive document metadata"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            metadata = {
                "url": url,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "title": None,
                "document_number": None,
                "document_type": None,
                "date_published": None,
                "date_effective": None,
                "authority": None,
                "jurisdiction": None,
                "language": None,
                "keywords": [],
                "classification": None
            }
            
            # Extract title from multiple sources
            title_sources = [
                soup.find('title'),
                soup.find('h1'),
                soup.find('meta', attrs={'name': 'title'}),
                soup.find('meta', attrs={'property': 'og:title'})
            ]
            
            for source in title_sources:
                if source and (source.string or source.get('content')):
                    metadata["title"] = (source.string or source.get('content')).strip()
                    break
            
            # Extract document number patterns
            text_content = soup.get_text()
            doc_number_patterns = [
                r'(?:Act|Law|Bill|Regulation)\s+(?:No\.?\s*)?(\d{4}/\d+|\d+/\d{4}|\d+)',
                r'(?:SI|S\.I\.|Statutory Instrument)\s+(\d{4}/\d+)',
                r'(?:Pub\.?\s*L\.?\s*No\.?\s*)(\d+-\d+)',
                r'(?:Document|Doc\.?)\s+(?:No\.?\s*)?(\d+)'
            ]
            
            for pattern in doc_number_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    metadata["document_number"] = match.group(1)
                    break
            
            # Extract dates
            date_patterns = [
                r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    metadata["date_published"] = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    break
            
            # Extract authority/jurisdiction from URL and content
            domain = urlparse(url).netloc.lower()
            if '.gov.uk' in domain or 'parliament.uk' in domain:
                metadata["jurisdiction"] = "uk"
                metadata["authority"] = "UK Government"
            elif '.gov' in domain:
                metadata["jurisdiction"] = "us" 
                metadata["authority"] = "US Government"
            elif '.europa.eu' in domain:
                metadata["jurisdiction"] = "eu"
                metadata["authority"] = "European Union"
            
            # Extract keywords from meta tags
            keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_meta and keywords_meta.get('content'):
                metadata["keywords"] = [kw.strip() for kw in keywords_meta.get('content').split(',')]
            
            # Determine document type
            if any(term in text_content.lower() for term in ['regulation', 'regulatory']):
                metadata["document_type"] = "regulation"
            elif any(term in text_content.lower() for term in ['act', 'statute']):
                metadata["document_type"] = "act"
            elif any(term in text_content.lower() for term in ['bill', 'draft']):
                metadata["document_type"] = "bill"
            
            # Language detection (basic)
            lang_attr = soup.find('html', attrs={'lang': True})
            if lang_attr:
                metadata["language"] = lang_attr.get('lang')
            
            return {
                "success": True,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting document metadata: {e}")
            return {"success": False, "error": str(e)}
    
    async def _follow_document_links(self, base_url: str, link_patterns: List[str] = None, 
                                   max_links: int = 10) -> Dict[str, Any]:
        """SDK Tool: Follow and extract content from document links"""
        try:
            link_patterns = link_patterns or [r'\.pdf$', r'\.doc$', r'\.docx$']
            
            # Get base page to find links
            base_result = await self._extract_static_html(base_url)
            if not base_result.get("success", False):
                return {"success": False, "error": "Could not access base URL"}
            
            document_links = base_result.get("document_links", [])
            
            # Filter links based on patterns
            filtered_links = []
            for link in document_links:
                if any(re.search(pattern, link, re.IGNORECASE) for pattern in link_patterns):
                    filtered_links.append(link)
                    if len(filtered_links) >= max_links:
                        break
            
            # Extract content from each link
            extracted_documents = []
            for link_url in filtered_links:
                try:
                    # For PDF and DOC files, we'd normally use specialized tools
                    # Here we'll just record the link for downstream processing
                    doc_info = {
                        "url": link_url,
                        "type": self._determine_document_type(link_url),
                        "accessible": True,
                        "extraction_method": "link_discovery"
                    }
                    
                    extracted_documents.append(doc_info)
                    
                except Exception as e:
                    self.logger.warning(f"Could not process link {link_url}: {e}")
                    extracted_documents.append({
                        "url": link_url,
                        "type": "unknown",
                        "accessible": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "base_url": base_url,
                "total_links_found": len(document_links),
                "filtered_links": len(filtered_links),
                "extracted_documents": extracted_documents,
                "extraction_method": "link_following"
            }
            
        except Exception as e:
            self.logger.error(f"Error following document links from {base_url}: {e}")
            return {"success": False, "error": str(e)}
    
    # Helper methods
    
    def _extract_page_title(self, soup: BeautifulSoup) -> str:
        """Extract page title from multiple sources"""
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return "No title found"
    
    def _extract_main_content(self, soup: BeautifulSoup, selectors: Dict[str, str] = None) -> str:
        """Extract main content using intelligent selectors"""
        selectors = selectors or {}
        
        # Try custom selectors first
        if 'content' in selectors:
            content_elem = soup.select_one(selectors['content'])
            if content_elem:
                return content_elem.get_text(separator='\n', strip=True)
        
        # Try common content selectors
        content_selectors = [
            'main', 
            'article',
            '.content',
            '#content',
            '.main-content',
            '.document-content',
            '.regulation-text'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator='\n', strip=True)
        
        # Fallback to body content, excluding navigation and footer
        body = soup.find('body')
        if body:
            # Remove common non-content elements
            for tag in body.find_all(['nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            return body.get_text(separator='\n', strip=True)
        
        return soup.get_text(separator='\n', strip=True)
    
    def _extract_basic_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract basic metadata from HTML"""
        metadata = {}
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def _extract_document_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract document links from page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                # Filter for document-like links
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xml', '.txt']):
                    links.append(full_url)
        
        return links[:20]  # Limit to first 20 links
    
    def _analyze_content_statistics(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Analyze content statistics"""
        text = soup.get_text()
        
        return {
            "word_count": len(text.split()),
            "character_count": len(text),
            "paragraph_count": len(text.split('\n\n')),
            "heading_count": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            "link_count": len(soup.find_all('a', href=True)),
            "table_count": len(soup.find_all('table')),
            "list_count": len(soup.find_all(['ul', 'ol']))
        }
    
    def _calculate_static_confidence(self, extraction_result: Dict[str, Any]) -> float:
        """Calculate confidence score for static extraction"""
        score = 0.0
        
        # Content length factor
        stats = extraction_result.get("content_statistics", {})
        word_count = stats.get("word_count", 0)
        if word_count > 1000:
            score += 0.4
        elif word_count > 500:
            score += 0.3
        elif word_count > 100:
            score += 0.2
        
        # Title presence
        if extraction_result.get("title") and len(extraction_result["title"]) > 10:
            score += 0.2
        
        # Structure indicators
        if stats.get("heading_count", 0) > 2:
            score += 0.2
        
        if stats.get("paragraph_count", 0) > 3:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_dynamic_confidence(self, extraction_result: Dict[str, Any]) -> float:
        """Calculate confidence score for dynamic extraction"""
        base_score = self._calculate_static_confidence(extraction_result)
        
        # JavaScript rendering bonus
        if extraction_result.get("javascript_rendered", False):
            base_score += 0.1
        
        # Dynamic elements bonus
        if extraction_result.get("dynamic_elements"):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def _find_next_page_url(self, current_url: str, pagination_selector: str) -> Optional[str]:
        """Find next page URL for pagination"""
        try:
            async with self.session.get(current_url) as response:
                if response.status != 200:
                    return None
                
                html_content = await response.text()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            next_link = soup.select_one(pagination_selector)
            
            if next_link and next_link.get('href'):
                return urljoin(current_url, next_link.get('href'))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding next page URL: {e}")
            return None
    
    def _consolidate_multi_page_content(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate content from multiple pages"""
        if not pages:
            return {"content": "", "metadata": {}}
        
        # Combine all content
        combined_content = []
        all_metadata = {}
        
        for page in pages:
            if page.get("content"):
                combined_content.append(f"=== Page {page['page_number']}: {page.get('title', 'Untitled')} ===\n")
                combined_content.append(page["content"])
                combined_content.append("\n\n")
            
            # Merge metadata
            page_metadata = page.get("metadata", {})
            for key, value in page_metadata.items():
                if key not in all_metadata:
                    all_metadata[key] = value
        
        return {
            "content": "\n".join(combined_content).strip(),
            "metadata": all_metadata,
            "page_count": len(pages),
            "total_word_count": sum(len(p.get("content", "").split()) for p in pages)
        }
    
    async def _extract_dynamic_elements(self, page) -> Dict[str, Any]:
        """Extract dynamic elements from Playwright page"""
        try:
            # Get information about JavaScript-rendered content
            script_count = await page.evaluate("document.scripts.length")
            
            # Check for common dynamic content indicators
            has_react = await page.evaluate("window.React !== undefined")
            has_angular = await page.evaluate("window.angular !== undefined")
            has_vue = await page.evaluate("window.Vue !== undefined")
            
            return {
                "script_count": script_count,
                "has_react": has_react,
                "has_angular": has_angular,
                "has_vue": has_vue,
                "page_loaded": True
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting dynamic elements: {e}")
            return {"error": str(e)}
    
    def _determine_document_type(self, url: str) -> str:
        """Determine document type from URL"""
        url_lower = url.lower()
        if url_lower.endswith('.pdf'):
            return "pdf"
        elif url_lower.endswith(('.doc', '.docx')):
            return "word_document"
        elif url_lower.endswith('.xml'):
            return "xml"
        elif url_lower.endswith('.txt'):
            return "text"
        else:
            return "unknown"
    
    async def _create_extraction_summary(self, job_id: str, result: Dict[str, Any], 
                                       context: SDKAgentContext) -> Dict[str, Any]:
        """Create comprehensive extraction summary"""
        # Process tool results from the SDK execution
        extracted_documents = []
        extraction_methods = set()
        challenges = []
        total_confidence = 0.0
        
        if context and hasattr(context, 'tool_results'):
            for tool_result in context.tool_results:
                if tool_result.status.value == "completed" and tool_result.result:
                    result_data = tool_result.result
                    if result_data.get("success"):
                        extraction_methods.add(result_data.get("extraction_method", "unknown"))
                        
                        # Create document entry
                        if result_data.get("main_content") or result_data.get("consolidated_content"):
                            doc = ExtractedDocument(
                                title=result_data.get("title", "Untitled Document"),
                                content=result_data.get("main_content") or result_data.get("consolidated_content", {}).get("content", ""),
                                document_type=result_data.get("metadata", {}).get("document_type", "unknown"),
                                url=result_data.get("url", ""),
                                metadata=result_data.get("metadata", {}),
                                confidence_score=result_data.get("confidence_score", 0.0),
                                word_count=result_data.get("content_statistics", {}).get("word_count", 0)
                            )
                            extracted_documents.append(doc.model_dump())
                            total_confidence += doc.confidence_score
                    else:
                        challenges.append(result_data.get("error", "Unknown extraction error"))
        
        # Create summary
        successful_extractions = len(extracted_documents)
        failed_extractions = len(challenges)
        average_confidence = total_confidence / successful_extractions if successful_extractions > 0 else 0.0
        
        summary = ExtractionSummary(
            total_documents=successful_extractions + failed_extractions,
            successful_extractions=successful_extractions,
            failed_extractions=failed_extractions,
            average_confidence=average_confidence,
            extraction_methods_used=list(extraction_methods),
            challenges_encountered=challenges,
            recommendations=self._generate_extraction_recommendations(extracted_documents, challenges)
        )
        
        return {
            "extraction_summary": summary.model_dump(),
            "extracted_documents": extracted_documents,
            "job_id": job_id,
            "agent_id": self.agent_id,
            "processing_completed_at": datetime.utcnow().isoformat()
        }
    
    def _generate_extraction_recommendations(self, documents: List[Dict], challenges: List[str]) -> List[str]:
        """Generate recommendations based on extraction results"""
        recommendations = []
        
        if not documents:
            recommendations.append("No content successfully extracted - consider alternative extraction methods")
            return recommendations
        
        avg_confidence = sum(doc.get("confidence_score", 0) for doc in documents) / len(documents)
        
        if avg_confidence < 0.5:
            recommendations.append("Low confidence scores detected - manual validation recommended")
        
        if any("timeout" in challenge.lower() for challenge in challenges):
            recommendations.append("Timeout issues detected - consider using dynamic extraction or reducing scope")
        
        if len(challenges) > len(documents):
            recommendations.append("High failure rate - review extraction strategy and selectors")
        
        word_counts = [doc.get("word_count", 0) for doc in documents]
        if word_counts and max(word_counts) < 100:
            recommendations.append("Extracted content appears incomplete - verify extraction selectors")
        
        return recommendations