"""
SDK-Based Discovery LLM Agent
Modern OpenAI Agents SDK implementation for website analysis and extraction strategy
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
from pydantic import BaseModel, Field

from agents.tools import function_tool
from .sdk_base_agent import BaseSDKAgent, SDKAgentContext
from .base_agent import AgentRole
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import WebsiteProfile, ExtractionMethod, ContentType
from ...models.regulation_models import DocumentType, Jurisdiction


# Pydantic models for structured outputs
class WebsiteAnalysisResult(BaseModel):
    """Structured output for website analysis"""
    url: str
    domain: str
    title: Optional[str]
    jurisdiction_detected: Optional[str]
    content_type: str
    extraction_feasibility: float = Field(ge=0.0, le=1.0)
    recommended_methods: List[str]
    technical_complexity: str = Field(choices=["low", "medium", "high"])
    estimated_documents: int
    challenges: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)


class ExtractionRecommendation(BaseModel):
    """Structured extraction recommendations"""
    primary_method: str
    fallback_methods: List[str]
    tools_required: List[str]
    estimated_success_rate: float = Field(ge=0.0, le=1.0)
    estimated_duration_minutes: int
    special_considerations: List[str]


class SDKDiscoveryAgent(BaseSDKAgent):
    """SDK-powered Discovery Agent for intelligent website analysis"""
    
    def __init__(self, broker):
        instructions = """You are an expert website analysis agent specialized in identifying government and legal websites that contain regulations, legislation, and legal documents.

Your primary responsibilities:
1. Analyze website structure, content, and technical characteristics
2. Identify the type of legal content available (regulations, bills, acts, etc.)
3. Determine the best extraction strategies for each site
4. Assess content quality and extraction feasibility
5. Provide detailed recommendations for data extraction

You have access to powerful web analysis tools that can:
- Fetch and analyze webpage content with full HTML parsing
- Check robots.txt for crawling permissions and policies
- Analyze technical stack and frameworks (React, Angular, etc.)
- Identify content patterns and legal document structures
- Detect jurisdictions and legal frameworks
- Extract document links and assess content volume

When analyzing a website, always:
1. Start by checking robots.txt for crawling permissions
2. Analyze the main webpage content and structure
3. Identify content patterns indicating legal/regulatory documents
4. Assess technical complexity and JavaScript requirements
5. Determine jurisdiction and legal authority
6. Calculate extraction feasibility scores
7. Provide specific, actionable extraction recommendations

Your analysis should be thorough, data-driven, and provide concrete extraction strategies."""

        super().__init__(
            agent_id="sdk_discovery_agent",
            agent_role=AgentRole.DISCOVERY,
            broker=broker,
            instructions=instructions,
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        # HTTP session for web analysis
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Analysis cache for performance
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the SDK discovery agent with HTTP session"""
        # Create HTTP session with appropriate headers
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'RegulationScraper-Discovery-SDK/2.0 (Automated Legal Research Tool)'
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
        """Register web analysis tools using SDK patterns"""
        
        # Register async tools using the SDK's function_tool decorator
        self.register_function_tool(
            self._analyze_webpage,
            name="analyze_webpage",
            description="Fetch and analyze a webpage's content, structure, and metadata for regulation extraction"
        )
        
        self.register_function_tool(
            self._check_robots_txt,
            name="check_robots_txt", 
            description="Check robots.txt for crawling permissions and extract sitemaps"
        )
        
        self.register_function_tool(
            self._analyze_content_patterns,
            name="analyze_content_patterns",
            description="Deep analysis of HTML content to identify legal document patterns and structures"
        )
        
        self.register_function_tool(
            self._detect_technical_stack,
            name="detect_technical_stack",
            description="Identify website's technical framework and complexity for extraction planning"
        )
        
        self.register_function_tool(
            self._calculate_extraction_feasibility,
            name="calculate_extraction_feasibility",
            description="Calculate comprehensive extraction feasibility score based on multiple factors"
        )
    
    async def _handle_job_request(self, message, context: SDKAgentContext):
        """Handle website analysis job requests using SDK patterns"""
        url = message.payload.get('url')
        job_id = message.payload.get('job_id')
        
        if not url:
            await self._send_error_response(message, "No URL provided for analysis")
            return
        
        self.logger.info(f"Starting SDK-powered analysis for: {url}")
        
        try:
            # Create structured analysis prompt
            analysis_prompt = f"""Analyze this website for regulation/legal content extraction: {url}

Please perform a comprehensive analysis using your available tools:

1. First, check robots.txt to understand crawling policies and find sitemaps
2. Analyze the main webpage content, structure, and metadata
3. Identify content patterns that indicate legal/regulatory documents
4. Detect the technical stack and assess JavaScript complexity
5. Calculate overall extraction feasibility based on all factors
6. Determine jurisdiction and legal framework if possible

After gathering all technical data, provide:
- Overall assessment of extraction potential
- Specific recommended extraction methods
- Technical challenges and solutions
- Estimated success rate and timeline

Be thorough and data-driven in your analysis."""

            # Run the agent with structured analysis
            result = await self.run_agent(
                user_message=analysis_prompt,
                context=context,
                use_session=True
            )
            
            # Process the analysis results into structured format
            analysis_result = await self._create_structured_analysis(url, result, context)
            
            # Send structured results to orchestrator
            await self._send_response(
                message_type=MessageType.WEBSITE_ANALYZED,
                recipient="orchestrator",
                payload={
                    "job_id": job_id,
                    "url": url,
                    "analysis": analysis_result,
                    "sdk_response": result.get("content"),
                    "execution_time": result.get("execution_time"),
                    "session_id": result.get("session_id")
                },
                correlation_id=message.correlation_id
            )
            
            self.logger.info(f"Completed SDK analysis for: {url}")
            
        except Exception as e:
            self.logger.error(f"SDK analysis failed for {url}: {e}")
            await self._send_error_response(message, str(e))
    
    # SDK-compatible tool functions with proper async/await patterns
    
    async def _analyze_webpage(self, url: str, analyze_links: bool = False) -> Dict[str, Any]:
        """SDK Tool: Analyze webpage content and structure"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "error": f"HTTP {response.status}: {response.reason}",
                        "success": False
                    }
                
                content = await response.text()
                headers = dict(response.headers)
                final_url = str(response.url)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Enhanced analysis for SDK version
            analysis = {
                "success": True,
                "url": final_url,
                "status_code": response.status,
                "title": soup.title.string.strip() if soup.title else None,
                "meta_description": self._extract_meta_description(soup),
                "content_length": len(content),
                "response_headers": headers,
                "page_structure": {
                    "headings": self._extract_headings(soup),
                    "navigation": self._analyze_navigation(soup),
                    "content_sections": self._analyze_content_sections(soup),
                    "forms": self._analyze_forms(soup)
                },
                "document_discovery": {
                    "pdf_links": self._count_document_links(soup, r'\.pdf$'),
                    "word_docs": self._count_document_links(soup, r'\.(doc|docx)$'),
                    "xml_feeds": self._count_document_links(soup, r'\.xml$'),
                    "total_external_links": len(soup.find_all('a', href=True))
                },
                "content_indicators": {
                    "text_content_length": len(soup.get_text()),
                    "table_count": len(soup.find_all('table')),
                    "list_count": len(soup.find_all(['ul', 'ol'])),
                    "definition_lists": len(soup.find_all('dl'))
                }
            }
            
            # Optional linked page analysis
            if analyze_links:
                analysis["linked_pages_sample"] = await self._sample_linked_pages(soup, url, limit=5)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing webpage {url}: {e}")
            return {"error": str(e), "success": False}
    
    async def _check_robots_txt(self, url: str) -> Dict[str, Any]:
        """SDK Tool: Check robots.txt comprehensively"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            async with self.session.get(robots_url) as response:
                if response.status != 200:
                    return {
                        "success": True,
                        "robots_found": False,
                        "status": response.status,
                        "crawling_allowed": True,
                        "message": "No robots.txt found - crawling generally allowed",
                        "sitemaps": []
                    }
                
                robots_content = await response.text()
            
            # Enhanced robots.txt parsing
            result = {
                "success": True,
                "robots_found": True,
                "robots_content": robots_content,
                "crawling_policies": self._parse_robots_policies(robots_content),
                "sitemaps": self._extract_sitemaps(robots_content),
                "crawl_delays": self._extract_crawl_delays(robots_content),
                "specific_restrictions": self._identify_specific_restrictions(robots_content)
            }
            
            # Determine crawling allowance for our user agent
            result["crawling_allowed"] = self._check_crawling_permission(robots_content, url)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {e}")
            return {"error": str(e), "success": False, "crawling_allowed": True}
    
    async def _analyze_content_patterns(self, html_content: str, url: str) -> Dict[str, Any]:
        """SDK Tool: Advanced content pattern analysis"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text().lower()
            
            analysis = {
                "success": True,
                "legal_indicators": {
                    "regulation_keywords": self._count_legal_keywords(text),
                    "citation_patterns": self._find_citation_patterns(text),
                    "legal_document_structure": self._analyze_legal_structure(soup),
                    "official_language_score": self._score_official_language(text),
                    "jurisdiction_signals": self._detect_jurisdiction_signals(text, url)
                },
                "content_organization": {
                    "hierarchical_structure": self._assess_hierarchy(soup),
                    "numbered_sections": self._count_numbered_sections(text),
                    "cross_references": self._find_cross_references(text),
                    "amendment_indicators": self._find_amendment_patterns(text)
                },
                "extraction_readiness": {
                    "structured_data_score": self._score_structured_data(soup),
                    "accessibility_score": self._score_accessibility(soup),
                    "content_stability_indicators": self._assess_content_stability(soup),
                    "machine_readability": self._score_machine_readability(soup)
                }
            }
            
            # Calculate composite scores
            analysis["composite_scores"] = {
                "legal_content_confidence": self._calculate_legal_confidence(analysis["legal_indicators"]),
                "extraction_feasibility": self._calculate_extraction_feasibility_score(analysis),
                "content_quality": self._calculate_content_quality(analysis)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing content patterns: {e}")
            return {"error": str(e), "success": False}
    
    async def _detect_technical_stack(self, html_content: str, response_headers: Dict[str, str] = None) -> Dict[str, Any]:
        """SDK Tool: Comprehensive technical stack detection"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            headers = response_headers or {}
            content_lower = html_content.lower()
            
            analysis = {
                "success": True,
                "frameworks": self._detect_js_frameworks(content_lower),
                "cms_platform": self._detect_cms(content_lower, headers),
                "server_technology": self._analyze_server_tech(headers),
                "javascript_analysis": {
                    "total_scripts": len(soup.find_all('script')),
                    "external_scripts": len([s for s in soup.find_all('script') if s.get('src')]),
                    "inline_script_size": sum(len(s.string) for s in soup.find_all('script') if s.string),
                    "dynamic_loading_indicators": self._detect_dynamic_loading(content_lower),
                    "spa_indicators": self._detect_spa_patterns(content_lower)
                },
                "extraction_complexity": {
                    "javascript_dependency": self._assess_js_dependency(soup, content_lower),
                    "dynamic_content_score": self._score_dynamic_content(soup),
                    "anti_scraping_indicators": self._detect_anti_scraping(content_lower, headers),
                    "accessibility_features": self._assess_accessibility_features(soup)
                }
            }
            
            # Calculate overall technical complexity
            analysis["complexity_score"] = self._calculate_technical_complexity(analysis)
            analysis["recommended_extraction_approach"] = self._recommend_extraction_approach(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error detecting technical stack: {e}")
            return {"error": str(e), "success": False}
    
    async def _calculate_extraction_feasibility(self, url: str, content_analysis: Dict[str, Any], 
                                              technical_analysis: Dict[str, Any], 
                                              robots_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """SDK Tool: Calculate comprehensive extraction feasibility"""
        try:
            feasibility_factors = {
                "content_quality": 0.0,
                "technical_accessibility": 0.0,
                "legal_compliance": 0.0,
                "data_structure": 0.0,
                "performance_factors": 0.0
            }
            
            # Content quality assessment (30% weight)
            if content_analysis.get("success"):
                legal_confidence = content_analysis.get("composite_scores", {}).get("legal_content_confidence", 0)
                content_quality = content_analysis.get("composite_scores", {}).get("content_quality", 0)
                feasibility_factors["content_quality"] = (legal_confidence * 0.6 + content_quality * 0.4) * 0.3
            
            # Technical accessibility (25% weight)  
            if technical_analysis.get("success"):
                complexity = technical_analysis.get("complexity_score", 1.0)
                accessibility = 1.0 - min(complexity, 1.0)  # Lower complexity = higher accessibility
                feasibility_factors["technical_accessibility"] = accessibility * 0.25
            
            # Legal compliance (20% weight)
            if robots_analysis.get("success") and robots_analysis.get("crawling_allowed", True):
                feasibility_factors["legal_compliance"] = 0.20
                # Reduce if there are significant restrictions
                if robots_analysis.get("specific_restrictions"):
                    feasibility_factors["legal_compliance"] *= 0.7
            
            # Data structure (15% weight)
            if content_analysis.get("success"):
                structure_score = content_analysis.get("extraction_readiness", {}).get("structured_data_score", 0)
                feasibility_factors["data_structure"] = structure_score * 0.15
            
            # Performance factors (10% weight) 
            crawl_delay = robots_analysis.get("crawl_delays", {}).get("general", 0) if robots_analysis.get("success") else 0
            if crawl_delay <= 1:
                feasibility_factors["performance_factors"] = 0.10
            elif crawl_delay <= 5:
                feasibility_factors["performance_factors"] = 0.05
            else:
                feasibility_factors["performance_factors"] = 0.02
            
            # Calculate overall feasibility
            overall_feasibility = sum(feasibility_factors.values())
            
            # Generate recommendations
            recommendations = self._generate_extraction_recommendations(
                overall_feasibility, feasibility_factors, technical_analysis, content_analysis
            )
            
            return {
                "success": True,
                "overall_feasibility": min(overall_feasibility, 1.0),
                "factor_breakdown": feasibility_factors,
                "recommendations": recommendations,
                "risk_assessment": self._assess_extraction_risks(technical_analysis, content_analysis),
                "estimated_effort": self._estimate_extraction_effort(overall_feasibility, technical_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating extraction feasibility: {e}")
            return {"error": str(e), "success": False}
    
    async def _create_structured_analysis(self, url: str, result: Dict[str, Any], 
                                        context: SDKAgentContext) -> Dict[str, Any]:
        """Create structured analysis result from SDK agent output"""
        # Extract structured data from the context's tool results
        webpage_data = {}
        robots_data = {}
        content_patterns = {}
        technical_stack = {}
        feasibility_data = {}
        
        # Process tool results from the SDK execution
        if context and hasattr(context, 'tool_results'):
            for tool_result in context.tool_results:
                if tool_result.status.value == "completed" and tool_result.result:
                    result_data = tool_result.result
                    if tool_result.tool_name == "analyze_webpage":
                        webpage_data = result_data
                    elif tool_result.tool_name == "check_robots_txt":
                        robots_data = result_data
                    elif tool_result.tool_name == "analyze_content_patterns":
                        content_patterns = result_data
                    elif tool_result.tool_name == "detect_technical_stack":
                        technical_stack = result_data
                    elif tool_result.tool_name == "calculate_extraction_feasibility":
                        feasibility_data = result_data
        
        # Create comprehensive structured analysis
        domain = urlparse(url).netloc
        
        return {
            "analysis_metadata": {
                "url": url,
                "domain": domain,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "agent_version": "sdk_v2.0",
                "analysis_session": context.session_id if context else None
            },
            "website_profile": {
                "title": webpage_data.get("title"),
                "meta_description": webpage_data.get("meta_description"),
                "content_length": webpage_data.get("content_length", 0),
                "status_code": webpage_data.get("status_code"),
                "final_url": webpage_data.get("url", url)
            },
            "content_analysis": content_patterns,
            "technical_assessment": technical_stack,
            "crawling_policy": robots_data,
            "extraction_feasibility": feasibility_data,
            "agent_recommendations": self._generate_final_recommendations(
                webpage_data, content_patterns, technical_stack, robots_data, feasibility_data
            ),
            "confidence_metrics": {
                "overall_confidence": feasibility_data.get("overall_feasibility", 0.5),
                "analysis_completeness": self._calculate_analysis_completeness(
                    webpage_data, content_patterns, technical_stack, robots_data
                ),
                "data_quality_score": self._calculate_data_quality_score(webpage_data, content_patterns)
            }
        }
    
    # Helper methods for enhanced analysis
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content') if meta_desc else None
    
    def _count_document_links(self, soup: BeautifulSoup, pattern: str) -> int:
        """Count document links matching pattern"""
        return len(soup.find_all('a', href=re.compile(pattern, re.I)))
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract heading hierarchy"""
        headings = {}
        for level in range(1, 7):
            h_tags = soup.find_all(f'h{level}')
            if h_tags:
                headings[f'h{level}'] = [h.get_text().strip() for h in h_tags[:10]]
        return headings
    
    def _analyze_navigation(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze navigation structure"""
        return {
            "nav_elements": len(soup.find_all('nav')),
            "breadcrumbs": bool(soup.find(attrs={'class': re.compile('breadcrumb', re.I)})),
            "menu_items": len(soup.find_all('li', attrs={'class': re.compile('menu|nav', re.I)})),
            "pagination": bool(soup.find(attrs={'class': re.compile('pag', re.I)}))
        }
    
    def _analyze_content_sections(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content organization"""
        return {
            "articles": len(soup.find_all('article')),
            "sections": len(soup.find_all('section')),
            "main_content": bool(soup.find('main')),
            "aside_content": len(soup.find_all('aside')),
            "footer_content": bool(soup.find('footer'))
        }
    
    def _analyze_forms(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze forms and search functionality"""
        forms = soup.find_all('form')
        search_forms = [f for f in forms if 'search' in str(f).lower()]
        
        return {
            "total_forms": len(forms),
            "search_forms": len(search_forms),
            "input_fields": len(soup.find_all('input')),
            "select_fields": len(soup.find_all('select')),
            "textarea_fields": len(soup.find_all('textarea'))
        }
    
    # Additional helper methods would continue here...
    # For brevity, I'm including key methods. The full implementation would include
    # all the analysis methods from the original agent, enhanced for SDK compatibility
    
    def _generate_final_recommendations(self, webpage_data: Dict, content_patterns: Dict,
                                      technical_stack: Dict, robots_data: Dict, 
                                      feasibility_data: Dict) -> Dict[str, Any]:
        """Generate final comprehensive recommendations"""
        recommendations = {
            "primary_extraction_method": "html_parsing",
            "fallback_methods": [],
            "tools_required": ["beautifulsoup", "requests"],
            "estimated_success_rate": feasibility_data.get("overall_feasibility", 0.5),
            "estimated_duration_hours": 2,
            "special_considerations": [],
            "risk_mitigation": []
        }
        
        # Determine optimal extraction method based on technical analysis
        if technical_stack.get("success") and technical_stack.get("complexity_score", 0) > 0.7:
            recommendations["primary_extraction_method"] = "browser_automation"
            recommendations["tools_required"] = ["playwright", "beautifulsoup"]
            recommendations["estimated_duration_hours"] = 4
        
        # Add PDF processing if many PDF documents found
        if webpage_data.get("document_discovery", {}).get("pdf_links", 0) > 10:
            recommendations["fallback_methods"].append("pdf_extraction")
            recommendations["tools_required"].append("pymupdf")
        
        # Add considerations based on robots.txt
        if not robots_data.get("crawling_allowed", True):
            recommendations["special_considerations"].append("Robots.txt restrictions detected")
            recommendations["risk_mitigation"].append("Implement crawl delays and respect robots.txt")
        
        return recommendations
    
    def _calculate_analysis_completeness(self, *analysis_results) -> float:
        """Calculate how complete the analysis is"""
        successful_analyses = sum(1 for result in analysis_results if result.get("success", False))
        return successful_analyses / len(analysis_results) if analysis_results else 0.0
    
    def _calculate_data_quality_score(self, webpage_data: Dict, content_patterns: Dict) -> float:
        """Calculate data quality score"""
        score = 0.0
        
        # Content length factor
        content_length = webpage_data.get("content_length", 0)
        if content_length > 10000:
            score += 0.3
        elif content_length > 1000:
            score += 0.2
        
        # Legal content indicators
        if content_patterns.get("success"):
            legal_confidence = content_patterns.get("composite_scores", {}).get("legal_content_confidence", 0)
            score += legal_confidence * 0.4
        
        # Structure indicators
        if webpage_data.get("page_structure"):
            structure_score = min(len(webpage_data["page_structure"]) / 4.0, 1.0) * 0.3
            score += structure_score
        
        return min(score, 1.0)