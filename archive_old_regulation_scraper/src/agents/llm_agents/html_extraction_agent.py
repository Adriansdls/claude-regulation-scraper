"""
HTML Extraction LLM Agent
Intelligent GPT-4 powered agent for extracting regulations from HTML pages
"""
import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag, NavigableString
from playwright.async_api import async_playwright, Browser, Page
import time

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractedContent, ContentType, ExtractionMethod, QualityLevel
from ...models.regulation_models import Regulation, DocumentType, DocumentStatus, LegalAuthority


class HTMLExtractionAgent(BaseLLMAgent):
    """Intelligent HTML extraction agent powered by GPT-4"""
    
    def __init__(self, broker):
        system_prompt = """You are an expert HTML extraction agent specialized in identifying and extracting regulatory and legal content from government websites.

Your core competencies:
1. Intelligent content identification using semantic understanding
2. Adaptive extraction strategies based on website structure  
3. Legal document structure recognition and parsing
4. Quality assessment and validation of extracted content
5. Handling of complex layouts, tables, and nested structures

Available extraction tools:
- Static HTML parsing with BeautifulSoup for well-structured content
- Dynamic browser automation with Playwright for JavaScript-heavy sites
- Content analysis and semantic understanding for regulation identification
- Structure mapping for hierarchical legal document organization
- Quality assessment for extracted content validation

When extracting content, focus on:
- Regulatory text, legal provisions, and official documents
- Document metadata (titles, identifiers, dates, authorities)
- Hierarchical structure (sections, articles, paragraphs)
- Relationships between documents and cross-references
- Official status and effective dates

Always prioritize:
1. Accuracy and completeness of legal content
2. Preservation of document structure and hierarchy  
3. Proper attribution and source identification
4. Quality scoring based on extraction confidence
5. Semantic understanding over simple text extraction

You should adapt your extraction strategy based on the website's characteristics and provide detailed analysis of the content quality and completeness."""

        super().__init__(
            agent_id="html_extraction_agent",
            agent_role=AgentRole.HTML_EXTRACTOR,
            broker=broker,
            system_prompt=system_prompt,
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # HTTP session for static content
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Playwright browser for dynamic content
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        # Content cache
        self.content_cache: Dict[str, Any] = {}
        
        # Extraction patterns for different document types
        self.extraction_patterns = {
            DocumentType.REGULATION: {
                "title_selectors": ["h1", ".regulation-title", ".document-title", "[class*='title']"],
                "content_selectors": [".regulation-content", ".document-body", "article", "main"],
                "section_selectors": [".section", ".article", "[class*='section']", "section"],
                "metadata_selectors": [".document-meta", ".regulation-info", ".metadata"]
            },
            DocumentType.ACT: {
                "title_selectors": ["h1", ".act-title", ".legislation-title"],
                "content_selectors": [".act-content", ".legislation-body", "main"],
                "section_selectors": [".part", ".chapter", ".section"],
                "metadata_selectors": [".act-info", ".legislation-meta"]
            },
            DocumentType.BILL: {
                "title_selectors": ["h1", ".bill-title"],
                "content_selectors": [".bill-content", ".bill-text"],
                "section_selectors": [".section", ".subsection"],
                "metadata_selectors": [".bill-info", ".bill-meta"]
            }
        }
    
    async def start(self):
        """Start the HTML extraction agent"""
        # Setup HTTP session
        timeout = aiohttp.ClientTimeout(total=60)
        headers = {
            'User-Agent': 'RegulationScraper-HTML/1.0 (Legal Document Extraction)'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        
        # Setup Playwright browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        await super().start()
    
    async def stop(self):
        """Stop the agent and cleanup resources"""
        if self.session:
            await self.session.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        await super().stop()
    
    async def _register_tools(self):
        """Register HTML extraction tools"""
        
        # Static HTML extraction tool
        self.register_tool(
            name="extract_static_html",
            function=self._extract_static_html,
            description="Extract content from static HTML using BeautifulSoup",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract content from"},
                    "content_selectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "CSS selectors for content extraction"
                    },
                    "document_type": {
                        "type": "string",
                        "enum": ["regulation", "act", "bill", "directive", "other"],
                        "description": "Expected document type for optimized extraction"
                    }
                },
                "required": ["url"]
            }
        )
        
        # Dynamic content extraction tool
        self.register_tool(
            name="extract_dynamic_content",
            function=self._extract_dynamic_content,
            description="Extract content from JavaScript-heavy pages using browser automation",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract content from"},
                    "wait_conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "CSS selectors to wait for before extraction"
                    },
                    "js_interactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["click", "scroll", "input"]},
                                "selector": {"type": "string"},
                                "value": {"type": "string"}
                            }
                        },
                        "description": "JavaScript interactions needed before extraction"
                    }
                },
                "required": ["url"]
            }
        )
        
        # Content analysis and structuring tool
        self.register_tool(
            name="analyze_content_structure",
            function=self._analyze_content_structure,
            description="Analyze and structure extracted HTML content for regulation parsing",
            parameters={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string", "description": "Raw HTML content to analyze"},
                    "url": {"type": "string", "description": "Source URL for context"},
                    "expected_structure": {
                        "type": "string",
                        "enum": ["hierarchical", "linear", "tabular", "mixed"],
                        "description": "Expected document structure type"
                    }
                },
                "required": ["html_content", "url"]
            }
        )
        
        # Regulation-specific extraction tool
        self.register_tool(
            name="extract_regulation_data",
            function=self._extract_regulation_data,
            description="Extract structured regulation data from parsed content",
            parameters={
                "type": "object",
                "properties": {
                    "structured_content": {
                        "type": "object",
                        "description": "Structured content from analysis"
                    },
                    "metadata_hints": {
                        "type": "object",
                        "description": "Metadata extraction hints from discovery"
                    }
                },
                "required": ["structured_content"]
            }
        )
        
        # Quality assessment tool
        self.register_tool(
            name="assess_extraction_quality",
            function=self._assess_extraction_quality,
            description="Assess the quality and completeness of extracted content",
            parameters={
                "type": "object",
                "properties": {
                    "extracted_data": {
                        "type": "object",
                        "description": "Extracted regulation data"
                    },
                    "original_content": {
                        "type": "string",
                        "description": "Original HTML content for comparison"
                    },
                    "extraction_method": {
                        "type": "string",
                        "description": "Method used for extraction"
                    }
                },
                "required": ["extracted_data"]
            }
        )
    
    async def _handle_job_request(self, message, context: AgentContext):
        """Handle HTML extraction job requests"""
        try:
            job_id = message.payload.get('job_id')
            task_data = message.payload.get('task_data', {})
            url = task_data.get('url')
            extraction_strategy = task_data.get('extraction_strategy', {})
            
            if not url:
                await self._send_error_response(message, "No URL provided for extraction")
                return
            
            self.logger.info(f"Starting HTML extraction for {url} (Job: {job_id})")
            
            # Use GPT-4 to plan and execute extraction
            extraction_prompt = f"""Extract regulatory content from this website: {url}

Job Details:
- Job ID: {job_id}  
- Extraction Strategy: {json.dumps(extraction_strategy, indent=2)}

Please analyze this extraction task and:

1. Determine the best extraction approach (static HTML vs dynamic content)
2. Extract the HTML content using appropriate tools
3. Analyze and structure the content for regulation identification
4. Extract structured regulation data with proper metadata
5. Assess the quality and completeness of the extraction

Focus on extracting:
- Complete regulatory text and legal provisions
- Document metadata (titles, identifiers, dates, status)
- Hierarchical structure (sections, articles, subsections)
- Authority information and jurisdiction details
- Cross-references and related documents

Provide comprehensive extraction with quality assessment."""

            # Execute extraction with tools
            response = await self.generate_response(
                user_message=extraction_prompt,
                context=context,
                use_tools=True
            )
            
            # Process extraction results
            extraction_results = await self._process_extraction_results(response, context, job_id, url)
            
            # Send results back to orchestrator
            await self._send_response(
                message_type=MessageType.CONTENT_EXTRACTED,
                recipient="orchestrator_agent",
                payload={
                    "job_id": job_id,
                    "agent_id": self.agent_id,
                    "results": extraction_results,
                    "extraction_time": response.get("execution_time"),
                    "token_usage": response.get("token_usage")
                },
                correlation_id=message.correlation_id
            )
            
            self.logger.info(f"Completed HTML extraction for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"HTML extraction failed: {e}")
            await self._send_error_response(message, str(e))
    
    async def _extract_static_html(self, url: str, content_selectors: List[str] = None, 
                                  document_type: str = "regulation") -> Dict[str, Any]:
        """Tool: Extract content from static HTML"""
        try:
            # Fetch HTML content
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}: {response.reason}"}
                
                html_content = await response.text()
                headers = dict(response.headers)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get extraction patterns for document type
            doc_type = DocumentType(document_type) if document_type in [t.value for t in DocumentType] else DocumentType.OTHER
            patterns = self.extraction_patterns.get(doc_type, self.extraction_patterns[DocumentType.REGULATION])
            
            # Extract content using patterns
            extraction_result = {
                "url": url,
                "html_content": html_content,
                "content_length": len(html_content),
                "title": self._extract_title(soup, patterns["title_selectors"]),
                "main_content": self._extract_main_content(soup, patterns["content_selectors"]),
                "sections": self._extract_sections(soup, patterns["section_selectors"]),
                "metadata": self._extract_metadata(soup, patterns["metadata_selectors"]),
                "links": self._extract_links(soup, url),
                "tables": self._extract_tables(soup),
                "lists": self._extract_lists(soup)
            }
            
            # Add content quality indicators
            extraction_result["quality_indicators"] = {
                "has_structured_content": bool(extraction_result["sections"]),
                "has_metadata": bool(extraction_result["metadata"]),
                "content_completeness": len(extraction_result["main_content"]) / max(1, len(html_content)),
                "has_legal_indicators": self._check_legal_indicators(soup.get_text())
            }
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Static HTML extraction failed: {e}")
            return {"error": str(e)}
    
    async def _extract_dynamic_content(self, url: str, wait_conditions: List[str] = None, 
                                      js_interactions: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Tool: Extract content from JavaScript-heavy pages"""
        try:
            if not self.browser:
                return {"error": "Browser not available"}
            
            wait_conditions = wait_conditions or []
            js_interactions = js_interactions or []
            
            # Create new page
            page = await self.browser.new_page()
            
            try:
                # Navigate to page
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for specified conditions
                for condition in wait_conditions:
                    try:
                        await page.wait_for_selector(condition, timeout=10000)
                    except Exception as e:
                        self.logger.warning(f"Wait condition failed: {condition} - {e}")
                
                # Perform JavaScript interactions
                for interaction in js_interactions:
                    try:
                        action = interaction.get("action")
                        selector = interaction.get("selector")
                        value = interaction.get("value")
                        
                        if action == "click" and selector:
                            await page.click(selector)
                            await page.wait_for_timeout(1000)  # Wait 1 second
                        elif action == "input" and selector and value:
                            await page.fill(selector, value)
                        elif action == "scroll":
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(2000)
                            
                    except Exception as e:
                        self.logger.warning(f"Interaction failed: {interaction} - {e}")
                
                # Wait a bit more for dynamic content to load
                await page.wait_for_timeout(3000)
                
                # Get final HTML content
                html_content = await page.content()
                title = await page.title()
                
                # Parse with BeautifulSoup for structured extraction
                soup = BeautifulSoup(html_content, 'html.parser')
                
                extraction_result = {
                    "url": url,
                    "html_content": html_content,
                    "page_title": title,
                    "content_length": len(html_content),
                    "main_content": self._extract_main_content(soup),
                    "sections": self._extract_sections(soup),
                    "metadata": self._extract_metadata(soup),
                    "dynamic_elements": await self._extract_dynamic_elements(page),
                    "screenshot_taken": False
                }
                
                # Take screenshot for visual verification if needed
                try:
                    screenshot = await page.screenshot()
                    extraction_result["screenshot_taken"] = True
                    # Could save screenshot for debugging or visual processing
                except Exception as e:
                    self.logger.warning(f"Screenshot failed: {e}")
                
                return extraction_result
                
            finally:
                await page.close()
                
        except Exception as e:
            self.logger.error(f"Dynamic content extraction failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_content_structure(self, html_content: str, url: str, 
                                       expected_structure: str = "hierarchical") -> Dict[str, Any]:
        """Tool: Analyze and structure HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analyze document structure
            structure_analysis = {
                "document_type": self._identify_document_type(soup, url),
                "hierarchy": self._analyze_hierarchy(soup),
                "content_organization": self._analyze_content_organization(soup),
                "metadata_structure": self._analyze_metadata_structure(soup),
                "navigation_structure": self._analyze_navigation_structure(soup)
            }
            
            # Create structured content representation
            structured_content = {
                "title": self._extract_title(soup),
                "abstract": self._extract_abstract(soup),
                "sections": self._create_hierarchical_sections(soup),
                "metadata": self._extract_comprehensive_metadata(soup, url),
                "references": self._extract_references(soup, url),
                "appendices": self._extract_appendices(soup)
            }
            
            # Quality assessment
            quality_metrics = {
                "structure_clarity": self._assess_structure_clarity(structure_analysis),
                "content_completeness": self._assess_content_completeness(structured_content),
                "metadata_quality": self._assess_metadata_quality(structured_content["metadata"]),
                "extraction_confidence": self._calculate_extraction_confidence(structure_analysis, structured_content)
            }
            
            return {
                "structure_analysis": structure_analysis,
                "structured_content": structured_content,
                "quality_metrics": quality_metrics,
                "extraction_strategy": self._recommend_extraction_strategy(structure_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Content structure analysis failed: {e}")
            return {"error": str(e)}
    
    async def _extract_regulation_data(self, structured_content: Dict[str, Any], 
                                     metadata_hints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tool: Extract structured regulation data"""
        try:
            metadata_hints = metadata_hints or {}
            
            # Extract core regulation information
            regulation_data = {
                "title": structured_content.get("title", ""),
                "document_type": self._determine_document_type(structured_content, metadata_hints),
                "status": self._determine_document_status(structured_content),
                "authority": self._extract_authority_info(structured_content),
                "jurisdiction": self._determine_jurisdiction(structured_content, metadata_hints),
                "identifiers": self._extract_identifiers(structured_content),
                "dates": self._extract_date_information(structured_content),
                "content": self._format_regulation_content(structured_content),
                "structure": self._create_regulation_structure(structured_content),
                "references": structured_content.get("references", []),
                "metadata": self._create_regulation_metadata(structured_content, metadata_hints)
            }
            
            # Add quality and confidence metrics
            regulation_data["extraction_quality"] = {
                "completeness_score": self._calculate_completeness_score(regulation_data),
                "confidence_score": self._calculate_confidence_score(regulation_data),
                "quality_flags": self._identify_quality_issues(regulation_data)
            }
            
            return regulation_data
            
        except Exception as e:
            self.logger.error(f"Regulation data extraction failed: {e}")
            return {"error": str(e)}
    
    async def _assess_extraction_quality(self, extracted_data: Dict[str, Any], 
                                       original_content: str = None,
                                       extraction_method: str = None) -> Dict[str, Any]:
        """Tool: Assess quality and completeness of extraction"""
        try:
            quality_assessment = {
                "overall_quality": QualityLevel.FAIR,  # Default
                "completeness_score": 0.0,
                "accuracy_indicators": {},
                "quality_issues": [],
                "recommendations": []
            }
            
            # Assess completeness
            completeness_factors = []
            
            if extracted_data.get("title"):
                completeness_factors.append(0.15)
            if extracted_data.get("content") and len(str(extracted_data["content"])) > 500:
                completeness_factors.append(0.25)
            if extracted_data.get("metadata") and len(extracted_data["metadata"]) > 3:
                completeness_factors.append(0.20)
            if extracted_data.get("structure") and extracted_data["structure"]:
                completeness_factors.append(0.20)
            if extracted_data.get("identifiers"):
                completeness_factors.append(0.10)
            if extracted_data.get("dates"):
                completeness_factors.append(0.10)
            
            completeness_score = sum(completeness_factors)
            quality_assessment["completeness_score"] = completeness_score
            
            # Determine overall quality level
            if completeness_score >= 0.9:
                quality_assessment["overall_quality"] = QualityLevel.EXCELLENT
            elif completeness_score >= 0.75:
                quality_assessment["overall_quality"] = QualityLevel.GOOD
            elif completeness_score >= 0.6:
                quality_assessment["overall_quality"] = QualityLevel.FAIR
            else:
                quality_assessment["overall_quality"] = QualityLevel.POOR
            
            # Identify quality issues
            if not extracted_data.get("title"):
                quality_assessment["quality_issues"].append("Missing document title")
            if not extracted_data.get("content") or len(str(extracted_data["content"])) < 100:
                quality_assessment["quality_issues"].append("Insufficient content extracted")
            if not extracted_data.get("metadata") or len(extracted_data["metadata"]) < 2:
                quality_assessment["quality_issues"].append("Limited metadata available")
            
            # Generate recommendations
            if completeness_score < 0.7:
                quality_assessment["recommendations"].append("Consider alternative extraction methods")
            if not extracted_data.get("structure"):
                quality_assessment["recommendations"].append("Improve structure detection and parsing")
            
            return quality_assessment
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return {"error": str(e)}
    
    async def _process_extraction_results(self, response: Dict[str, Any], context: AgentContext,
                                        job_id: str, url: str) -> Dict[str, Any]:
        """Process and format extraction results"""
        # Combine results from all tool calls
        combined_results = {
            "job_id": job_id,
            "url": url,
            "extraction_method": ExtractionMethod.HTML_PARSING,
            "agent_response": response.get("content"),
            "extracted_regulations": [],
            "quality_assessment": {},
            "processing_metadata": {
                "extraction_time": response.get("execution_time"),
                "token_usage": response.get("token_usage"),
                "tools_used": []
            }
        }
        
        # Process tool results
        for tool_result in context.tool_results:
            if tool_result.status.value == "completed" and tool_result.result and not tool_result.result.get("error"):
                combined_results["processing_metadata"]["tools_used"].append(tool_result.tool_name)
                
                # Process regulation data extraction results
                if tool_result.tool_name == "extract_regulation_data" and tool_result.result:
                    regulation_data = tool_result.result
                    if not regulation_data.get("error"):
                        combined_results["extracted_regulations"].append(regulation_data)
                
                # Process quality assessment results
                elif tool_result.tool_name == "assess_extraction_quality" and tool_result.result:
                    combined_results["quality_assessment"] = tool_result.result
        
        # Calculate overall success metrics
        combined_results["extraction_success"] = {
            "regulations_found": len(combined_results["extracted_regulations"]),
            "overall_quality": combined_results.get("quality_assessment", {}).get("overall_quality", "unknown"),
            "completeness_score": combined_results.get("quality_assessment", {}).get("completeness_score", 0.0),
            "extraction_successful": len(combined_results["extracted_regulations"]) > 0
        }
        
        return combined_results
    
    # Helper methods for content extraction
    
    def _extract_title(self, soup: BeautifulSoup, selectors: List[str] = None) -> str:
        """Extract document title"""
        selectors = selectors or ["h1", "title", ".title", ".document-title"]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        
        # Fallback to page title
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ""
    
    def _extract_main_content(self, soup: BeautifulSoup, selectors: List[str] = None) -> str:
        """Extract main content"""
        selectors = selectors or ["main", "article", ".content", ".document-body", ".regulation-content"]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Remove navigation and footer elements
                for tag in element.find_all(['nav', 'footer', '.nav', '.footer']):
                    tag.decompose()
                return element.get_text(separator=' ', strip=True)
        
        # Fallback to body content
        body = soup.find('body')
        if body:
            # Remove script, style, nav, footer
            for tag in body.find_all(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            return body.get_text(separator=' ', strip=True)[:5000]  # Limit to 5000 chars
        
        return ""
    
    def _extract_sections(self, soup: BeautifulSoup, selectors: List[str] = None) -> List[Dict[str, Any]]:
        """Extract document sections"""
        selectors = selectors or [".section", "section", ".article", ".part", "[class*='section']"]
        sections = []
        
        for selector in selectors:
            elements = soup.select(selector)
            for i, element in enumerate(elements[:20]):  # Limit to 20 sections
                section_title = ""
                heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading:
                    section_title = heading.get_text().strip()
                
                sections.append({
                    "index": i,
                    "title": section_title,
                    "content": element.get_text(separator=' ', strip=True)[:2000],  # Limit content
                    "selector": selector
                })
            
            if sections:  # If we found sections with this selector, stop trying others
                break
        
        return sections
    
    def _extract_metadata(self, soup: BeautifulSoup, selectors: List[str] = None) -> Dict[str, str]:
        """Extract document metadata"""
        metadata = {}
        
        # Extract from meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property') or tag.get('http-equiv')
            content = tag.get('content')
            if name and content:
                metadata[name] = content
        
        # Look for structured metadata sections
        selectors = selectors or [".metadata", ".document-info", ".regulation-info"]
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Extract key-value pairs
                pairs = element.find_all(['dt', 'dd'])
                for i in range(0, len(pairs) - 1, 2):
                    if pairs[i].name == 'dt' and pairs[i + 1].name == 'dd':
                        key = pairs[i].get_text().strip()
                        value = pairs[i + 1].get_text().strip()
                        metadata[key] = value
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract relevant links"""
        links = []
        
        for link in soup.find_all('a', href=True)[:50]:  # Limit to 50 links
            href = link.get('href')
            text = link.get_text().strip()
            
            if href and text:
                full_url = urljoin(base_url, href)
                links.append({
                    "url": full_url,
                    "text": text,
                    "type": self._classify_link(href, text)
                })
        
        return links
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables with structure"""
        tables = []
        
        for i, table in enumerate(soup.find_all('table')[:10]):  # Limit to 10 tables
            headers = []
            rows = []
            
            # Extract headers
            header_row = table.find('thead') or table.find('tr')
            if header_row:
                headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
            
            # Extract data rows
            for row in table.find_all('tr')[1:11]:  # Skip header, limit to 10 rows
                cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if headers or rows:
                tables.append({
                    "index": i,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "column_count": len(headers) or (len(rows[0]) if rows else 0)
                })
        
        return tables
    
    def _extract_lists(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract lists with structure"""
        lists = []
        
        for i, list_elem in enumerate(soup.find_all(['ul', 'ol', 'dl'])[:10]):  # Limit to 10 lists
            list_type = list_elem.name
            items = []
            
            if list_type in ['ul', 'ol']:
                items = [li.get_text().strip() for li in list_elem.find_all('li')[:20]]
            elif list_type == 'dl':
                # Definition list
                dts = list_elem.find_all('dt')
                dds = list_elem.find_all('dd')
                items = [{"term": dt.get_text().strip(), 
                         "definition": dd.get_text().strip() if i < len(dds) else ""} 
                        for i, dt in enumerate(dts[:10])]
            
            if items:
                lists.append({
                    "index": i,
                    "type": list_type,
                    "items": items,
                    "item_count": len(items)
                })
        
        return lists
    
    def _check_legal_indicators(self, text: str) -> bool:
        """Check for legal document indicators"""
        legal_keywords = [
            'regulation', 'act', 'bill', 'law', 'statute', 'code',
            'section', 'article', 'paragraph', 'subsection',
            'whereas', 'pursuant', 'hereby', 'shall', 'effective'
        ]
        
        text_lower = text.lower()
        return sum(1 for keyword in legal_keywords if keyword in text_lower) >= 3
    
    def _classify_link(self, href: str, text: str) -> str:
        """Classify link type"""
        href_lower = href.lower()
        text_lower = text.lower()
        
        if '.pdf' in href_lower:
            return 'pdf_document'
        elif '.doc' in href_lower or '.docx' in href_lower:
            return 'word_document'
        elif any(word in text_lower for word in ['regulation', 'act', 'bill', 'law']):
            return 'legal_document'
        elif any(word in text_lower for word in ['archive', 'historical', 'past']):
            return 'archive'
        else:
            return 'general'
    
    def _identify_document_type(self, soup: BeautifulSoup, url: str) -> str:
        """Identify the type of legal document"""
        text = soup.get_text().lower()
        url_lower = url.lower()
        
        # URL-based detection
        if 'regulation' in url_lower:
            return 'regulation'
        elif 'act' in url_lower:
            return 'act'
        elif 'bill' in url_lower:
            return 'bill'
        elif 'directive' in url_lower:
            return 'directive'
        
        # Content-based detection
        doc_type_indicators = {
            'regulation': ['regulation', 'regulatory', 'rule', 'statutory instrument'],
            'act': ['act', 'public law', 'statute'],
            'bill': ['bill', 'proposed', 'draft'],
            'directive': ['directive', 'guideline', 'instruction']
        }
        
        scores = {}
        for doc_type, indicators in doc_type_indicators.items():
            scores[doc_type] = sum(text.count(indicator) for indicator in indicators)
        
        return max(scores.items(), key=lambda x: x[1])[0] if any(scores.values()) else 'other'
    
    def _analyze_hierarchy(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze document hierarchy"""
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not headings:
            return {"has_hierarchy": False, "depth": 0, "structure": []}
        
        structure = []
        for heading in headings[:20]:  # Limit to 20 headings
            level = int(heading.name[1])
            text = heading.get_text().strip()
            structure.append({"level": level, "text": text})
        
        return {
            "has_hierarchy": True,
            "depth": max(h["level"] for h in structure),
            "heading_count": len(structure),
            "structure": structure
        }
    
    def _analyze_content_organization(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content organization"""
        return {
            "sections": len(soup.find_all(['section', '.section'])),
            "articles": len(soup.find_all(['article', '.article'])),
            "paragraphs": len(soup.find_all('p')),
            "lists": len(soup.find_all(['ul', 'ol', 'dl'])),
            "tables": len(soup.find_all('table')),
            "has_toc": bool(soup.find(attrs={'class': re.compile('toc|table.*content', re.I)}))
        }
    
    def _analyze_metadata_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze metadata structure"""
        meta_elements = soup.find_all('meta')
        structured_meta = soup.find_all(attrs={'class': re.compile('meta|info', re.I)})
        
        return {
            "meta_tags": len(meta_elements),
            "structured_metadata": len(structured_meta),
            "has_schema": bool(soup.find(attrs={'itemscope': True})),
            "has_json_ld": bool(soup.find('script', type='application/ld+json'))
        }
    
    def _analyze_navigation_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze navigation structure"""
        return {
            "nav_elements": len(soup.find_all('nav')),
            "breadcrumbs": bool(soup.find(attrs={'class': re.compile('breadcrumb', re.I)})),
            "pagination": bool(soup.find(attrs={'class': re.compile('pag', re.I)})),
            "internal_links": len([a for a in soup.find_all('a', href=True) if not a['href'].startswith('http')])
        }
    
    async def _extract_dynamic_elements(self, page: Page) -> Dict[str, Any]:
        """Extract dynamic elements from page"""
        try:
            # Get JavaScript-loaded content
            dynamic_content = await page.evaluate("""
                () => {
                    return {
                        dynamicText: document.querySelectorAll('[data-loaded="true"]').length,
                        ajaxContent: document.querySelectorAll('.ajax-loaded').length,
                        lazyImages: document.querySelectorAll('img[loading="lazy"]').length
                    };
                }
            """)
            return dynamic_content
        except Exception as e:
            self.logger.warning(f"Failed to extract dynamic elements: {e}")
            return {}
    
    def _extract_abstract(self, soup: BeautifulSoup) -> str:
        """Extract document abstract or summary"""
        abstract_selectors = ['.abstract', '.summary', '.overview', '[class*="abstract"]', '[class*="summary"]']
        
        for selector in abstract_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator=' ', strip=True)
        
        # Fallback: first paragraph that's long enough
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 100:  # At least 100 characters
                return text
        
        return ""
    
    def _create_hierarchical_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Create hierarchical section structure"""
        sections = []
        current_section = None
        
        # Find all headings and content
        elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section'])
        
        for element in elements[:100]:  # Limit processing
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # New section
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    "level": int(element.name[1]),
                    "title": element.get_text().strip(),
                    "content": [],
                    "subsections": []
                }
            
            elif current_section and element.get_text().strip():
                # Add content to current section
                text = element.get_text().strip()
                if len(text) > 20:  # Only substantial content
                    current_section["content"].append({
                        "type": element.name,
                        "text": text[:500]  # Limit text length
                    })
        
        if current_section:
            sections.append(current_section)
        
        return sections[:20]  # Limit to 20 sections
    
    def _extract_comprehensive_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract comprehensive metadata"""
        metadata = {}
        
        # Basic metadata
        metadata.update(self._extract_metadata(soup))
        
        # Document-specific metadata
        metadata["source_url"] = url
        metadata["extraction_date"] = datetime.utcnow().isoformat()
        
        # Look for dates in content
        text = soup.get_text()
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates_found.extend(matches[:5])  # Limit to 5 dates per pattern
        
        if dates_found:
            metadata["dates_found"] = dates_found[:10]  # Limit to 10 total dates
        
        return metadata
    
    def _extract_references(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract document references"""
        references = []
        
        # Look for reference sections
        ref_sections = soup.find_all(attrs={'class': re.compile('ref|citation', re.I)})
        for section in ref_sections:
            links = section.find_all('a', href=True)
            for link in links[:20]:  # Limit per section
                references.append({
                    "text": link.get_text().strip(),
                    "url": urljoin(base_url, link['href']),
                    "type": "reference"
                })
        
        # Also look for legal citations in text
        text = soup.get_text()
        citation_patterns = [
            r'\b\d+\s+U\.S\.C\.\s+§?\s*\d+',
            r'\bPub\.\s*L\.\s*No\.\s*\d+-\d+',
            r'\b\d{4}/\d+/[A-Z]+'
        ]
        
        for pattern in citation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:10]:  # Limit matches
                references.append({
                    "text": match,
                    "type": "citation"
                })
        
        return references[:50]  # Limit total references
    
    def _extract_appendices(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract appendices or annexes"""
        appendices = []
        
        appendix_selectors = [
            '[class*="appendix"]', '[class*="annex"]', '[class*="schedule"]',
            'section[id*="appendix"]', 'div[id*="annex"]'
        ]
        
        for selector in appendix_selectors:
            elements = soup.select(selector)
            for i, element in enumerate(elements[:5]):  # Limit to 5 appendices
                title = ""
                heading = element.find(['h1', 'h2', 'h3', 'h4'])
                if heading:
                    title = heading.get_text().strip()
                
                appendices.append({
                    "index": i,
                    "title": title or f"Appendix {i+1}",
                    "content": element.get_text(separator=' ', strip=True)[:1000]  # Limit content
                })
        
        return appendices
    
    # Quality assessment methods
    
    def _assess_structure_clarity(self, structure_analysis: Dict[str, Any]) -> float:
        """Assess structure clarity score"""
        score = 0.0
        
        if structure_analysis.get("hierarchy", {}).get("has_hierarchy"):
            score += 0.3
        
        if structure_analysis.get("content_organization", {}).get("sections", 0) > 0:
            score += 0.2
        
        if structure_analysis.get("content_organization", {}).get("has_toc"):
            score += 0.2
        
        if structure_analysis.get("navigation_structure", {}).get("breadcrumbs"):
            score += 0.15
        
        if structure_analysis.get("metadata_structure", {}).get("structured_metadata", 0) > 0:
            score += 0.15
        
        return min(1.0, score)
    
    def _assess_content_completeness(self, structured_content: Dict[str, Any]) -> float:
        """Assess content completeness score"""
        score = 0.0
        
        if structured_content.get("title"):
            score += 0.2
        
        if structured_content.get("sections") and len(structured_content["sections"]) > 0:
            score += 0.3
        
        if structured_content.get("metadata") and len(structured_content["metadata"]) > 3:
            score += 0.2
        
        if structured_content.get("references"):
            score += 0.15
        
        if structured_content.get("abstract"):
            score += 0.15
        
        return min(1.0, score)
    
    def _assess_metadata_quality(self, metadata: Dict[str, Any]) -> float:
        """Assess metadata quality score"""
        if not metadata:
            return 0.0
        
        quality_indicators = [
            "author", "date", "title", "description", "keywords",
            "identifier", "publisher", "language", "subject"
        ]
        
        score = 0.0
        for indicator in quality_indicators:
            if any(indicator in key.lower() for key in metadata.keys()):
                score += 1.0 / len(quality_indicators)
        
        return min(1.0, score)
    
    def _calculate_extraction_confidence(self, structure_analysis: Dict[str, Any], 
                                       structured_content: Dict[str, Any]) -> float:
        """Calculate overall extraction confidence"""
        structure_score = self._assess_structure_clarity(structure_analysis)
        content_score = self._assess_content_completeness(structured_content)
        metadata_score = self._assess_metadata_quality(structured_content.get("metadata", {}))
        
        return (structure_score * 0.4 + content_score * 0.4 + metadata_score * 0.2)
    
    def _recommend_extraction_strategy(self, structure_analysis: Dict[str, Any]) -> List[str]:
        """Recommend extraction strategy based on analysis"""
        strategies = ["html_parsing"]  # Always include basic HTML parsing
        
        # Add JavaScript execution if needed
        js_complexity = structure_analysis.get("content_organization", {}).get("sections", 0)
        if js_complexity == 0:  # Might need JavaScript if no sections found
            strategies.append("javascript_execution")
        
        # Add table extraction if tables present
        if structure_analysis.get("content_organization", {}).get("tables", 0) > 0:
            strategies.append("table_extraction")
        
        # Add reference extraction if references found
        if structure_analysis.get("navigation_structure", {}).get("internal_links", 0) > 10:
            strategies.append("link_following")
        
        return strategies
    
    # Regulation data formatting methods
    
    def _determine_document_type(self, structured_content: Dict[str, Any], 
                                metadata_hints: Dict[str, Any]) -> str:
        """Determine document type from content and hints"""
        title = structured_content.get("title", "").lower()
        
        # Check title for type indicators
        if "regulation" in title:
            return DocumentType.REGULATION.value
        elif "act" in title:
            return DocumentType.ACT.value
        elif "bill" in title:
            return DocumentType.BILL.value
        elif "directive" in title:
            return DocumentType.DIRECTIVE.value
        
        # Check metadata hints
        discovery_type = metadata_hints.get("document_type")
        if discovery_type:
            return discovery_type
        
        return DocumentType.OTHER.value
    
    def _determine_document_status(self, structured_content: Dict[str, Any]) -> str:
        """Determine document status"""
        content_text = str(structured_content).lower()
        
        if "in force" in content_text or "effective" in content_text:
            return DocumentStatus.IN_FORCE.value
        elif "draft" in content_text or "proposed" in content_text:
            return DocumentStatus.PROPOSED.value
        elif "repealed" in content_text:
            return DocumentStatus.REPEALED.value
        
        return DocumentStatus.ENACTED.value
    
    def _extract_authority_info(self, structured_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract authority information"""
        metadata = structured_content.get("metadata", {})
        
        authority = {
            "name": metadata.get("publisher") or metadata.get("author") or "Unknown",
            "type": "government",
            "jurisdiction": "unknown"
        }
        
        # Look for authority info in content
        for section in structured_content.get("sections", []):
            section_text = section.get("title", "").lower()
            if "department" in section_text or "ministry" in section_text:
                authority["name"] = section.get("title", "").strip()
                break
        
        return authority
    
    def _determine_jurisdiction(self, structured_content: Dict[str, Any], 
                              metadata_hints: Dict[str, Any]) -> str:
        """Determine jurisdiction from content and hints"""
        # Check metadata hints first
        if metadata_hints.get("jurisdiction"):
            return metadata_hints["jurisdiction"]
        
        # Analyze content for jurisdiction indicators
        content_text = str(structured_content).lower()
        
        if "united kingdom" in content_text or "uk government" in content_text:
            return "uk"
        elif "european union" in content_text or "european commission" in content_text:
            return "eu"
        elif "united states" in content_text or "us government" in content_text:
            return "us"
        
        return "other"
    
    def _extract_identifiers(self, structured_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document identifiers"""
        metadata = structured_content.get("metadata", {})
        identifiers = {}
        
        # Look for common identifier fields
        for key, value in metadata.items():
            key_lower = key.lower()
            if any(term in key_lower for term in ["id", "number", "identifier", "reference"]):
                identifiers[key] = value
        
        # Look for identifiers in title
        title = structured_content.get("title", "")
        id_patterns = [
            r'\b\d{4}/\d+\b',  # EU style
            r'\bSI\s+\d{4}/\d+\b',  # UK SI
            r'\bNo\.\s*\d+\s*of\s*\d{4}\b'  # General numbering
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                identifiers["primary_id"] = match.group()
                break
        
        return identifiers
    
    def _extract_date_information(self, structured_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract date information"""
        metadata = structured_content.get("metadata", {})
        dates = {}
        
        # Look for date fields in metadata
        for key, value in metadata.items():
            key_lower = key.lower()
            if "date" in key_lower:
                dates[key] = value
        
        # Extract dates from found dates list
        dates_found = metadata.get("dates_found", [])
        if dates_found:
            dates["extracted_dates"] = dates_found[:5]
        
        return dates
    
    def _format_regulation_content(self, structured_content: Dict[str, Any]) -> str:
        """Format regulation content"""
        content_parts = []
        
        # Add title
        if structured_content.get("title"):
            content_parts.append(f"Title: {structured_content['title']}")
        
        # Add abstract
        if structured_content.get("abstract"):
            content_parts.append(f"Abstract: {structured_content['abstract']}")
        
        # Add sections
        for section in structured_content.get("sections", []):
            if section.get("title"):
                content_parts.append(f"\nSection: {section['title']}")
            
            for content_item in section.get("content", []):
                if content_item.get("text"):
                    content_parts.append(content_item["text"])
        
        return "\n\n".join(content_parts)
    
    def _create_regulation_structure(self, structured_content: Dict[str, Any]) -> Dict[str, Any]:
        """Create regulation structure representation"""
        structure = {
            "sections": [],
            "chapters": [],
            "articles": [],
            "definitions": {},
            "references": []
        }
        
        # Process sections
        for section in structured_content.get("sections", []):
            structure["sections"].append({
                "level": section.get("level", 1),
                "title": section.get("title", ""),
                "content_summary": section.get("content", [{}])[0].get("text", "")[:200] if section.get("content") else ""
            })
        
        # Process references
        for ref in structured_content.get("references", []):
            structure["references"].append({
                "text": ref.get("text", ""),
                "type": ref.get("type", "unknown")
            })
        
        return structure
    
    def _create_regulation_metadata(self, structured_content: Dict[str, Any], 
                                   metadata_hints: Dict[str, Any]) -> Dict[str, Any]:
        """Create regulation metadata"""
        base_metadata = structured_content.get("metadata", {})
        
        regulation_metadata = {
            "extraction_method": "html_parsing",
            "extraction_date": datetime.utcnow().isoformat(),
            "content_length": len(str(structured_content)),
            "sections_count": len(structured_content.get("sections", [])),
            "references_count": len(structured_content.get("references", [])),
            "has_structure": bool(structured_content.get("sections")),
            "language": base_metadata.get("language", "en")
        }
        
        # Add discovery hints
        if metadata_hints:
            regulation_metadata.update(metadata_hints)
        
        return regulation_metadata
    
    def _calculate_completeness_score(self, regulation_data: Dict[str, Any]) -> float:
        """Calculate completeness score for regulation data"""
        score_factors = []
        
        if regulation_data.get("title"):
            score_factors.append(0.15)
        if regulation_data.get("content") and len(regulation_data["content"]) > 500:
            score_factors.append(0.25)
        if regulation_data.get("authority", {}).get("name") != "Unknown":
            score_factors.append(0.10)
        if regulation_data.get("identifiers"):
            score_factors.append(0.10)
        if regulation_data.get("dates"):
            score_factors.append(0.10)
        if regulation_data.get("structure", {}).get("sections"):
            score_factors.append(0.20)
        if regulation_data.get("metadata", {}).get("sections_count", 0) > 0:
            score_factors.append(0.10)
        
        return sum(score_factors)
    
    def _calculate_confidence_score(self, regulation_data: Dict[str, Any]) -> float:
        """Calculate confidence score for regulation data"""
        confidence_factors = []
        
        # Content quality indicators
        if regulation_data.get("content") and len(regulation_data["content"]) > 1000:
            confidence_factors.append(0.3)
        elif regulation_data.get("content") and len(regulation_data["content"]) > 500:
            confidence_factors.append(0.2)
        
        # Structure indicators
        if regulation_data.get("structure", {}).get("sections"):
            confidence_factors.append(0.25)
        
        # Metadata indicators
        if len(regulation_data.get("metadata", {})) > 5:
            confidence_factors.append(0.2)
        elif len(regulation_data.get("metadata", {})) > 3:
            confidence_factors.append(0.15)
        
        # Authority information
        if regulation_data.get("authority", {}).get("name") != "Unknown":
            confidence_factors.append(0.15)
        
        # Document type identification
        if regulation_data.get("document_type") != "other":
            confidence_factors.append(0.1)
        
        return min(1.0, sum(confidence_factors))
    
    def _identify_quality_issues(self, regulation_data: Dict[str, Any]) -> List[str]:
        """Identify quality issues with extracted regulation data"""
        issues = []
        
        if not regulation_data.get("title"):
            issues.append("missing_title")
        
        if not regulation_data.get("content") or len(regulation_data["content"]) < 100:
            issues.append("insufficient_content")
        
        if not regulation_data.get("structure", {}).get("sections"):
            issues.append("no_structured_sections")
        
        if regulation_data.get("authority", {}).get("name") == "Unknown":
            issues.append("unknown_authority")
        
        if not regulation_data.get("identifiers"):
            issues.append("missing_identifiers")
        
        if regulation_data.get("document_type") == "other":
            issues.append("unidentified_document_type")
        
        return issues