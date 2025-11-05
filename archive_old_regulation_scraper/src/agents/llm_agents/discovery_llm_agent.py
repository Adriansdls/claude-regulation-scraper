"""
Discovery LLM Agent
Intelligent GPT-4 powered agent for website analysis and extraction strategy determination
"""
import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from datetime import datetime
from bs4 import BeautifulSoup
import re

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import WebsiteProfile, ExtractionMethod, ContentType
from ...models.regulation_models import DocumentType, Jurisdiction


class DiscoveryLLMAgent(BaseLLMAgent):
    """Intelligent Discovery Agent powered by GPT-4"""
    
    def __init__(self, broker):
        system_prompt = """You are an expert website analysis agent specialized in identifying government and legal websites that contain regulations, legislation, and legal documents.

Your primary responsibilities:
1. Analyze website structure, content, and technical characteristics
2. Identify the type of legal content available (regulations, bills, acts, etc.)
3. Determine the best extraction strategies for each site
4. Assess content quality and extraction feasibility
5. Provide detailed recommendations for data extraction

You have access to powerful web analysis tools that can:
- Fetch and analyze webpage content
- Check robots.txt for crawling permissions  
- Analyze technical stack and frameworks
- Identify content patterns and structures
- Detect jurisdictions and legal frameworks

When analyzing a website, consider:
- Content structure and organization
- Technical complexity (JavaScript, dynamic content)
- Document types and formats available
- Legal jurisdiction and authority
- Accessibility and extraction feasibility
- Quality indicators and reliability

Always provide structured, actionable analysis with specific extraction recommendations."""

        super().__init__(
            agent_id="discovery_llm_agent",
            agent_role=AgentRole.DISCOVERY,
            broker=broker,
            system_prompt=system_prompt,
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        # HTTP session for web analysis
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Analysis cache
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the discovery agent with HTTP session"""
        # Create HTTP session with appropriate headers
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'RegulationScraper-Discovery/1.0 (Automated Legal Research Tool)'
        }
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        )
        
        await super().start()
    
    async def stop(self):
        """Stop the discovery agent and cleanup resources"""
        if self.session:
            await self.session.close()
        await super().stop()
    
    async def _register_tools(self):
        """Register web analysis tools"""
        # Website content analysis tool
        self.register_tool(
            name="analyze_webpage",
            function=self._analyze_webpage,
            description="Fetch and analyze a webpage's content, structure, and metadata",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to analyze"
                    },
                    "analyze_links": {
                        "type": "boolean", 
                        "description": "Whether to analyze linked pages for document discovery",
                        "default": False
                    }
                },
                "required": ["url"]
            }
        )
        
        # Robots.txt analysis tool
        self.register_tool(
            name="check_robots_txt",
            function=self._check_robots_txt,
            description="Check robots.txt for crawling permissions and policies",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The base URL to check robots.txt for"
                    }
                },
                "required": ["url"]
            }
        )
        
        # Content pattern analysis tool
        self.register_tool(
            name="analyze_content_patterns",
            function=self._analyze_content_patterns,
            description="Deep analysis of content patterns for regulation identification",
            parameters={
                "type": "object", 
                "properties": {
                    "html_content": {
                        "type": "string",
                        "description": "HTML content to analyze for patterns"
                    },
                    "url": {
                        "type": "string", 
                        "description": "Source URL for context"
                    }
                },
                "required": ["html_content", "url"]
            }
        )
        
        # Technical stack detection tool  
        self.register_tool(
            name="detect_technical_stack",
            function=self._detect_technical_stack,
            description="Identify website's technical stack and complexity",
            parameters={
                "type": "object",
                "properties": {
                    "html_content": {
                        "type": "string",
                        "description": "HTML content to analyze"
                    },
                    "response_headers": {
                        "type": "object",
                        "description": "HTTP response headers",
                        "default": {}
                    }
                },
                "required": ["html_content"]
            }
        )
    
    async def _handle_job_request(self, message, context: AgentContext):
        """Handle website analysis job requests"""
        url = message.payload.get('url')
        job_id = message.payload.get('job_id')
        
        if not url:
            await self._send_error_response(message, "No URL provided for analysis")
            return
        
        self.logger.info(f"Starting intelligent analysis for: {url}")
        
        try:
            # Generate intelligent analysis using GPT-4
            analysis_prompt = f"""Analyze this website for regulation/legal content extraction: {url}

Please perform a comprehensive analysis using your available tools to:

1. First, check the robots.txt to understand crawling policies
2. Analyze the main webpage content and structure  
3. Identify content patterns that indicate legal/regulatory documents
4. Assess the technical complexity and requirements
5. Determine the jurisdiction and legal framework
6. Recommend optimal extraction strategies

Provide a detailed analysis with specific, actionable recommendations for extracting regulatory content from this site."""

            # Generate response with tool usage
            response = await self.generate_response(
                user_message=analysis_prompt,
                context=context,
                use_tools=True
            )
            
            # Process the analysis results
            analysis_result = await self._process_analysis_results(url, response, context)
            
            # Send results to orchestrator
            await self._send_response(
                message_type=MessageType.WEBSITE_ANALYZED,
                recipient="orchestrator",
                payload={
                    "job_id": job_id,
                    "url": url,
                    "analysis": analysis_result,
                    "agent_response": response.get("content"),
                    "tool_results": [r.result for r in context.tool_results if r.result],
                    "execution_time": response.get("execution_time"),
                    "token_usage": response.get("token_usage")
                },
                correlation_id=message.correlation_id
            )
            
            self.logger.info(f"Completed analysis for: {url}")
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {url}: {e}")
            await self._send_error_response(message, str(e))
    
    async def _analyze_webpage(self, url: str, analyze_links: bool = False) -> Dict[str, Any]:
        """Tool: Analyze webpage content and structure"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}: {response.reason}"}
                
                content = await response.text()
                headers = dict(response.headers)
                final_url = str(response.url)
                
            # Parse content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Basic analysis
            analysis = {
                "url": final_url,
                "status_code": response.status,
                "title": soup.title.string if soup.title else None,
                "meta_description": None,
                "content_length": len(content),
                "response_headers": headers
            }
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                analysis["meta_description"] = meta_desc.get('content')
            
            # Content structure analysis
            analysis.update({
                "headings": self._extract_headings(soup),
                "navigation_elements": self._analyze_navigation(soup),  
                "content_sections": self._analyze_content_sections(soup),
                "forms_and_search": self._analyze_forms(soup),
                "document_links": self._find_document_links(soup, url),
                "text_content_sample": soup.get_text()[:1000]  # First 1000 chars
            })
            
            # Link analysis if requested
            if analyze_links:
                analysis["linked_pages"] = await self._analyze_linked_pages(soup, url)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing webpage {url}: {e}")
            return {"error": str(e)}
    
    async def _check_robots_txt(self, url: str) -> Dict[str, Any]:
        """Tool: Check robots.txt for crawling permissions"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            async with self.session.get(robots_url) as response:
                if response.status != 200:
                    return {
                        "robots_found": False,
                        "status": response.status,
                        "crawling_allowed": True,  # Default to allowed if no robots.txt
                        "message": "No robots.txt found - crawling generally allowed"
                    }
                
                robots_content = await response.text()
            
            # Parse robots.txt
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            user_agent = 'RegulationScraper-Discovery/1.0'
            
            result = {
                "robots_found": True,
                "robots_content": robots_content,
                "crawling_allowed": rp.can_fetch(user_agent, url),
                "crawl_delay": rp.crawl_delay(user_agent),
                "sitemaps": list(rp.site_maps()) if hasattr(rp, 'site_maps') else []
            }
            
            # Extract additional policies
            lines = robots_content.lower().split('\n')
            policies = []
            for line in lines:
                line = line.strip()
                if line.startswith('disallow:') or line.startswith('allow:'):
                    policies.append(line)
            
            result["policies"] = policies
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {e}")
            return {"error": str(e), "crawling_allowed": True}
    
    async def _analyze_content_patterns(self, html_content: str, url: str) -> Dict[str, Any]:
        """Tool: Analyze content patterns for regulation identification"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text().lower()
            
            # Legal document patterns
            legal_patterns = {
                "regulation_keywords": self._count_legal_keywords(text),
                "citation_patterns": self._find_citation_patterns(text),
                "document_structure": self._analyze_document_structure(soup),
                "official_language": self._detect_official_language(text),
                "jurisdiction_indicators": self._detect_jurisdiction_indicators(text, url)
            }
            
            # Content organization patterns
            organization_patterns = {
                "hierarchical_content": self._check_hierarchical_structure(soup),
                "numbered_sections": self._count_numbered_sections(text),
                "definition_lists": len(soup.find_all('dl')),
                "data_tables": self._analyze_data_tables(soup),
                "search_functionality": self._detect_search_features(soup)
            }
            
            # Document availability indicators
            document_patterns = {
                "pdf_links": len(soup.find_all('a', href=re.compile(r'\.pdf$', re.I))),
                "word_docs": len(soup.find_all('a', href=re.compile(r'\.(doc|docx)$', re.I))),
                "archive_links": self._find_archive_links(soup),
                "pagination": self._detect_pagination(soup),
                "filtering_options": self._count_filter_options(soup)
            }
            
            return {
                "legal_patterns": legal_patterns,
                "organization_patterns": organization_patterns, 
                "document_patterns": document_patterns,
                "extraction_readiness_score": self._calculate_extraction_readiness(
                    legal_patterns, organization_patterns, document_patterns
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing content patterns: {e}")
            return {"error": str(e)}
    
    async def _detect_technical_stack(self, html_content: str, response_headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Tool: Detect technical stack and complexity"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            headers = response_headers or {}
            
            # Framework detection
            frameworks = []
            content_lower = html_content.lower()
            
            framework_indicators = {
                "react": ["react", "data-reactroot", "_react"],
                "angular": ["angular", "ng-app", "ng-version"],
                "vue": ["vue.js", "v-app", "__vue__"],
                "jquery": ["jquery", "$.fn.jquery"],
                "bootstrap": ["bootstrap", "btn btn-", "container-fluid"]
            }
            
            for framework, indicators in framework_indicators.items():
                if any(indicator in content_lower for indicator in indicators):
                    frameworks.append(framework)
            
            # JavaScript complexity
            scripts = soup.find_all('script')
            js_complexity = {
                "script_count": len(scripts),
                "external_scripts": len([s for s in scripts if s.get('src')]),
                "inline_scripts": len([s for s in scripts if s.string and len(s.string) > 100]),
                "dynamic_loading": bool(re.search(r'loading|spinner|lazy', content_lower))
            }
            
            # Server technology from headers
            server_tech = {
                "server": headers.get('server', 'unknown'),
                "powered_by": headers.get('x-powered-by', 'unknown'),
                "content_type": headers.get('content-type', 'text/html')
            }
            
            # Content Management System detection
            cms_indicators = {
                "wordpress": ["wp-content", "wp-includes", "wordpress"],
                "drupal": ["drupal", "sites/all", "sites/default"],
                "sharepoint": ["sharepoint", "_layouts", "SP.UI"]
            }
            
            detected_cms = None
            for cms, indicators in cms_indicators.items():
                if any(indicator in content_lower for indicator in indicators):
                    detected_cms = cms
                    break
            
            return {
                "frameworks": frameworks,
                "javascript_complexity": js_complexity,
                "server_technology": server_tech, 
                "cms": detected_cms,
                "complexity_score": self._calculate_technical_complexity(js_complexity, frameworks)
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting technical stack: {e}")
            return {"error": str(e)}
    
    async def _process_analysis_results(self, url: str, response: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Process and structure the analysis results"""
        # Extract key information from tool results
        website_data = {}
        robots_data = {}
        content_patterns = {}
        technical_stack = {}
        
        for tool_result in context.tool_results:
            if tool_result.status.value == "completed" and tool_result.result:
                if tool_result.tool_name == "analyze_webpage":
                    website_data = tool_result.result
                elif tool_result.tool_name == "check_robots_txt":
                    robots_data = tool_result.result
                elif tool_result.tool_name == "analyze_content_patterns":
                    content_patterns = tool_result.result
                elif tool_result.tool_name == "detect_technical_stack":
                    technical_stack = tool_result.result
        
        # Create structured analysis
        domain = urlparse(url).netloc
        
        analysis = {
            "website_profile": {
                "domain": domain,
                "url": url,
                "title": website_data.get("title"),
                "meta_description": website_data.get("meta_description"),
                "content_length": website_data.get("content_length", 0),
                "analysis_timestamp": datetime.utcnow().isoformat()
            },
            "technical_assessment": technical_stack,
            "content_analysis": content_patterns,
            "crawling_policy": robots_data,
            "extraction_recommendations": self._generate_extraction_recommendations(
                website_data, content_patterns, technical_stack, robots_data
            ),
            "confidence_score": self._calculate_confidence_score(
                website_data, content_patterns, technical_stack
            )
        }
        
        return analysis
    
    def _generate_extraction_recommendations(self, website_data: Dict, content_patterns: Dict, 
                                           technical_stack: Dict, robots_data: Dict) -> Dict[str, Any]:
        """Generate specific extraction strategy recommendations"""
        recommendations = {
            "primary_methods": [],
            "secondary_methods": [],
            "tools_required": [],
            "challenges": [],
            "estimated_success_rate": 0.0
        }
        
        # Determine primary extraction methods
        js_complex = technical_stack.get("javascript_complexity", {}).get("script_count", 0) > 10
        pdf_heavy = content_patterns.get("document_patterns", {}).get("pdf_links", 0) > 5
        structured_content = content_patterns.get("organization_patterns", {}).get("hierarchical_content", False)
        
        if structured_content and not js_complex:
            recommendations["primary_methods"].append("html_parsing")
            recommendations["estimated_success_rate"] += 0.4
        
        if js_complex:
            recommendations["primary_methods"].append("browser_automation")
            recommendations["tools_required"].append("playwright")
            recommendations["challenges"].append("JavaScript dependency")
            recommendations["estimated_success_rate"] += 0.3
        
        if pdf_heavy:
            recommendations["secondary_methods"].append("pdf_extraction")
            recommendations["tools_required"].append("pdf_processing")
            recommendations["estimated_success_rate"] += 0.2
        
        # Add crawling considerations
        if not robots_data.get("crawling_allowed", True):
            recommendations["challenges"].append("Robots.txt restrictions")
            recommendations["estimated_success_rate"] *= 0.7
        
        crawl_delay = robots_data.get("crawl_delay")
        if crawl_delay and crawl_delay > 5:
            recommendations["challenges"].append(f"Long crawl delay: {crawl_delay}s")
        
        return recommendations
    
    def _calculate_confidence_score(self, website_data: Dict, content_patterns: Dict, 
                                   technical_stack: Dict) -> float:
        """Calculate confidence score for the analysis"""
        score_factors = []
        
        # Content quality factor
        content_length = website_data.get("content_length", 0)
        if content_length > 10000:
            score_factors.append(0.9)
        elif content_length > 1000:
            score_factors.append(0.7)
        else:
            score_factors.append(0.4)
        
        # Legal content indicators
        legal_score = content_patterns.get("legal_patterns", {}).get("regulation_keywords", 0)
        if legal_score > 10:
            score_factors.append(0.9)
        elif legal_score > 5:
            score_factors.append(0.7)
        else:
            score_factors.append(0.5)
        
        # Technical analysis completeness
        if technical_stack and not technical_stack.get("error"):
            score_factors.append(0.8)
        else:
            score_factors.append(0.4)
        
        return sum(score_factors) / len(score_factors) if score_factors else 0.5
    
    # Helper methods for content analysis
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract heading structure"""
        headings = {}
        for level in range(1, 7):
            h_tags = soup.find_all(f'h{level}')
            if h_tags:
                headings[f'h{level}'] = [h.get_text().strip() for h in h_tags[:10]]
        return headings
    
    def _analyze_navigation(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze navigation elements"""
        return {
            "nav_elements": len(soup.find_all('nav')),
            "breadcrumbs": bool(soup.find(attrs={'class': re.compile('breadcrumb', re.I)})),
            "menu_items": len(soup.find_all('li', attrs={'class': re.compile('menu|nav', re.I)}))
        }
    
    def _analyze_content_sections(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content organization"""
        return {
            "articles": len(soup.find_all('article')),
            "sections": len(soup.find_all('section')),
            "main_content": bool(soup.find('main')),
            "aside_content": len(soup.find_all('aside'))
        }
    
    def _analyze_forms(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze forms and search functionality"""
        forms = soup.find_all('form')
        search_forms = [f for f in forms if 'search' in str(f).lower()]
        
        return {
            "total_forms": len(forms),
            "search_forms": len(search_forms),
            "input_fields": len(soup.find_all('input')),
            "select_fields": len(soup.find_all('select'))
        }
    
    def _find_document_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[str]]:
        """Find links to documents"""
        pdf_links = [urljoin(base_url, a.get('href', '')) for a in soup.find_all('a', href=re.compile(r'\.pdf$', re.I))]
        doc_links = [urljoin(base_url, a.get('href', '')) for a in soup.find_all('a', href=re.compile(r'\.(doc|docx)$', re.I))]
        
        return {
            "pdf_documents": pdf_links[:20],  # Limit to first 20
            "word_documents": doc_links[:20]
        }
    
    def _count_legal_keywords(self, text: str) -> int:
        """Count legal keywords in text"""
        legal_keywords = [
            'regulation', 'act', 'bill', 'law', 'statute', 'code',
            'section', 'article', 'paragraph', 'subsection',
            'legislation', 'regulatory', 'legal', 'compliance',
            'enforcement', 'authority', 'jurisdiction', 'whereas'
        ]
        
        return sum(text.count(keyword) for keyword in legal_keywords)
    
    def _find_citation_patterns(self, text: str) -> int:
        """Find legal citation patterns"""
        citation_patterns = [
            r'\b\d+\s+U\.S\.C\.\s+',
            r'\bPub\.\s*L\.\s*No\.',
            r'\b\d{4}/\d+/[A-Z]+',
            r'\bSI\s+\d{4}/\d+',
            r'\bNo\.\s*\d+\s*of\s*\d{4}'
        ]
        
        total_citations = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            total_citations += len(matches)
        
        return total_citations
    
    def _analyze_document_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze document structure indicators"""
        return {
            "numbered_lists": len(soup.find_all('ol')),
            "definition_lists": len(soup.find_all('dl')),
            "data_tables": len(soup.find_all('table')),
            "hierarchical_headings": len(soup.find_all(['h1', 'h2', 'h3', 'h4'])),
            "sectioned_content": len(soup.find_all('section'))
        }
    
    def _detect_official_language(self, text: str) -> bool:
        """Detect formal/official language patterns"""
        formal_indicators = [
            'official', 'government', 'department', 'ministry',
            'federal', 'national', 'state', 'authority',
            'pursuant', 'whereas', 'hereby', 'thereof'
        ]
        
        return sum(1 for indicator in formal_indicators if indicator in text) >= 3
    
    def _detect_jurisdiction_indicators(self, text: str, url: str) -> Dict[str, Any]:
        """Detect jurisdiction and legal framework"""
        domain = urlparse(url).netloc.lower()
        
        # Domain-based jurisdiction detection
        jurisdiction = None
        if '.gov.uk' in domain or 'parliament.uk' in domain:
            jurisdiction = 'uk'
        elif '.europa.eu' in domain or '.eur-lex.europa.eu' in domain:
            jurisdiction = 'eu'
        elif '.gov' in domain and not '.gov.uk' in domain:
            jurisdiction = 'us'
        elif '.gc.ca' in domain:
            jurisdiction = 'canada'
        elif '.gov.au' in domain:
            jurisdiction = 'australia'
        
        # Content-based indicators
        jurisdiction_keywords = {
            'uk': ['united kingdom', 'uk government', 'parliament'],
            'eu': ['european union', 'european commission'],
            'us': ['united states', 'us government', 'congress'],
            'canada': ['government of canada', 'canada'],
            'australia': ['australian government', 'australia']
        }
        
        keyword_scores = {}
        for jur, keywords in jurisdiction_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                keyword_scores[jur] = score
        
        return {
            "detected_jurisdiction": jurisdiction,
            "keyword_indicators": keyword_scores,
            "confidence": 0.9 if jurisdiction else (0.7 if keyword_scores else 0.3)
        }
    
    def _check_hierarchical_structure(self, soup: BeautifulSoup) -> bool:
        """Check for hierarchical content structure"""
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if len(headings) < 3:
            return False
        
        # Check if headings follow logical order
        levels = [int(h.name[1]) for h in headings]
        return levels[0] <= 2 and not any(levels[i] - levels[i-1] > 2 for i in range(1, len(levels)))
    
    def _count_numbered_sections(self, text: str) -> int:
        """Count numbered sections in text"""
        patterns = [r'\b\d+\.\s', r'\b\d+\.\d+\s', r'\bSection\s+\d+', r'\bArticle\s+\d+']
        total = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            total += len(matches)
        return total
    
    def _analyze_data_tables(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze data tables"""
        tables = soup.find_all('table')
        complex_tables = 0
        
        for table in tables:
            if (table.find('thead') and table.find('tbody')) or len(table.find_all('tr')) > 10:
                complex_tables += 1
        
        return {
            "total_tables": len(tables),
            "complex_tables": complex_tables,
            "has_structured_data": complex_tables > 0
        }
    
    def _detect_search_features(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Detect search and filtering features"""
        search_inputs = soup.find_all('input', attrs={'type': 'search'})
        search_forms = soup.find_all('form', attrs={'class': re.compile('search', re.I)})
        filter_selects = soup.find_all('select')
        
        return {
            "search_inputs": len(search_inputs),
            "search_forms": len(search_forms), 
            "filter_options": len(filter_selects),
            "has_advanced_search": bool(soup.find(text=re.compile('advanced search', re.I)))
        }
    
    def _find_archive_links(self, soup: BeautifulSoup) -> int:
        """Find links to archives or historical documents"""
        archive_indicators = ['archive', 'historical', 'past', 'previous', 'year']
        archive_links = 0
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().lower()
            if any(indicator in link_text for indicator in archive_indicators):
                archive_links += 1
        
        return archive_links
    
    def _detect_pagination(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Detect pagination elements"""
        return {
            "pagination_elements": len(soup.find_all(attrs={'class': re.compile('pag', re.I)})),
            "next_prev_links": len(soup.find_all('a', text=re.compile('next|previous|prev', re.I))),
            "numbered_pages": len(soup.find_all('a', text=re.compile(r'^\d+$')))
        }
    
    def _count_filter_options(self, soup: BeautifulSoup) -> int:
        """Count filtering and sorting options"""
        return len(soup.find_all('select')) + len(soup.find_all('input', attrs={'type': 'checkbox'}))
    
    def _calculate_extraction_readiness(self, legal_patterns: Dict, organization_patterns: Dict, 
                                       document_patterns: Dict) -> float:
        """Calculate extraction readiness score"""
        score = 0.0
        
        # Legal content indicators (40% weight)
        legal_score = min(1.0, legal_patterns.get("regulation_keywords", 0) / 20)
        score += legal_score * 0.4
        
        # Organization quality (35% weight)
        org_score = 0.0
        if organization_patterns.get("hierarchical_content", False):
            org_score += 0.5
        if organization_patterns.get("data_tables", {}).get("has_structured_data", False):
            org_score += 0.3
        if organization_patterns.get("search_functionality", {}).get("search_forms", 0) > 0:
            org_score += 0.2
        score += min(1.0, org_score) * 0.35
        
        # Document availability (25% weight)
        doc_score = min(1.0, (document_patterns.get("pdf_links", 0) + 
                             document_patterns.get("word_docs", 0)) / 10)
        score += doc_score * 0.25
        
        return min(1.0, score)
    
    def _calculate_technical_complexity(self, js_complexity: Dict, frameworks: List[str]) -> float:
        """Calculate technical complexity score"""
        score = 0.0
        
        # JavaScript complexity
        script_count = js_complexity.get("script_count", 0)
        if script_count > 10:
            score += 0.4
        elif script_count > 5:
            score += 0.2
        
        # Framework complexity
        if 'react' in frameworks or 'angular' in frameworks:
            score += 0.3
        elif 'vue' in frameworks:
            score += 0.2
        elif 'jquery' in frameworks:
            score += 0.1
        
        # Dynamic loading
        if js_complexity.get("dynamic_loading", False):
            score += 0.3
        
        return min(1.0, score)
    
    async def _analyze_linked_pages(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Analyze linked pages for document discovery (optional deep analysis)"""
        links = []
        
        # Find document-related links
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx)$', re.I))
        
        for link in doc_links[:5]:  # Limit to 5 for performance
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                links.append({
                    "url": full_url,
                    "text": link.get_text().strip(),
                    "type": "document"
                })
        
        return links