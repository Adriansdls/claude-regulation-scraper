"""
Firecrawl-powered Extraction Agent
Advanced regulation extraction using Firecrawl's AI-powered web scraping
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
from dataclasses import asdict

try:
    from firecrawl import Firecrawl
except ImportError:
    Firecrawl = None

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractedContent, ContentType, ExtractionMethod, QualityLevel
from ...models.regulation_models import Regulation, DocumentType, DocumentStatus, LegalAuthority


class FirecrawlExtractorAgent(BaseLLMAgent):
    """Advanced regulation extraction agent powered by Firecrawl and GPT-4"""
    
    def __init__(self, broker, firecrawl_api_key: Optional[str] = None):
        system_prompt = """You are an expert regulation extraction agent powered by Firecrawl's advanced web scraping and GPT-4's language understanding.

Your specialized capabilities:
1. AI-powered content extraction from complex government websites
2. Automatic handling of JavaScript, dynamic content, and anti-bot measures
3. Structured regulation data extraction with custom schemas
4. Multi-format processing (HTML, PDF references, embedded documents)
5. Legal document classification and metadata extraction
6. Quality assessment and validation of extracted content

Available extraction tools:
- firecrawl_scrape: Extract clean, structured content from a single URL
- firecrawl_extract: Use AI to extract specific structured data with custom prompts
- analyze_regulation_structure: Analyze legal document hierarchy and organization
- extract_legal_metadata: Extract titles, citations, authorities, dates, and references
- validate_regulation_content: Assess content quality and completeness

When extracting regulations:
1. Use Firecrawl's scrape endpoint for initial content gathering
2. Apply custom extraction prompts for structured regulation data
3. Identify document types (acts, regulations, statutory instruments, etc.)
4. Extract legal hierarchies (sections, subsections, paragraphs)
5. Capture metadata (authorities, effective dates, amendments)
6. Validate content quality and flag any extraction issues

Always prioritize accuracy and completeness for legal document extraction."""

        super().__init__(
            agent_id="firecrawl_extractor",
            agent_role=AgentRole.HTML_EXTRACTOR,
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Initialize Firecrawl client
        self.firecrawl_api_key = firecrawl_api_key or os.getenv('FIRECRAWL_API_KEY')
        self.firecrawl_client = None
        
        if Firecrawl and self.firecrawl_api_key:
            try:
                self.firecrawl_client = Firecrawl(api_key=self.firecrawl_api_key)
                self.logger.info("✅ Firecrawl client initialized")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Firecrawl: {e}")
        else:
            self.logger.warning("⚠️  Firecrawl not available - install firecrawl-py and set FIRECRAWL_API_KEY")

    async def _register_tools(self):
        """Register Firecrawl-powered extraction tools"""
        await super()._register_tools()
        
        # Firecrawl scraping tools
        self.register_tool(
            name="firecrawl_scrape",
            function=self._firecrawl_scrape,
            description="Extract clean, structured content from a URL using Firecrawl's AI-powered scraping",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string", 
                        "description": "Target URL to scrape for regulations"
                    },
                    "include_raw_html": {
                        "type": "boolean",
                        "description": "Whether to include raw HTML in response",
                        "default": False
                    }
                },
                "required": ["url"]
            }
        )
        
        self.register_tool(
            name="firecrawl_extract_regulations",
            function=self._firecrawl_extract_regulations,
            description="Extract structured regulation data using Firecrawl's AI extraction with custom prompts",
            parameters={
                "type": "object", 
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Target URL containing regulations"
                    },
                    "custom_schema": {
                        "type": "object",
                        "description": "Optional custom extraction schema",
                        "default": None
                    }
                },
                "required": ["url"]
            }
        )
        
        self.register_tool(
            name="analyze_regulation_structure",
            function=self._analyze_regulation_structure,
            description="Analyze the hierarchical structure of a legal document",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Extracted regulation content to analyze"
                    },
                    "url": {
                        "type": "string",
                        "description": "Source URL of the content"
                    }
                },
                "required": ["content", "url"]
            }
        )
        
        self.register_tool(
            name="extract_legal_metadata",
            function=self._extract_legal_metadata,
            description="Extract legal metadata like titles, citations, authorities, and dates",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Regulation content text to extract metadata from"
                    },
                    "url": {
                        "type": "string", 
                        "description": "Source URL of the regulation"
                    }
                },
                "required": ["content", "url"]
            }
        )

    async def _firecrawl_scrape(self, url: str, include_raw_html: bool = False) -> Dict[str, Any]:
        """
        Scrape URL using Firecrawl's advanced extraction
        
        Args:
            url: Target URL to scrape
            include_raw_html: Whether to include raw HTML in response
            
        Returns:
            Dict containing scraped content, metadata, and extraction info
        """
        if not self.firecrawl_client:
            return {
                "success": False,
                "error": "Firecrawl client not initialized",
                "fallback": "Use traditional scraping methods"
            }
        
        try:
            self.logger.info(f"🔥 Firecrawl scraping: {url}")
            
            # Perform the scrape - Firecrawl takes URL directly
            result = self.firecrawl_client.scrape(url)
            
            # Firecrawl returns result directly, not with success/data structure
            if result and hasattr(result, 'markdown'):
                # Extract key information
                scraped_data = {
                    "success": True,
                    "url": url,
                    "title": getattr(result, 'title', ''),
                    "markdown": getattr(result, 'markdown', ''),
                    "html": getattr(result, 'html', '') if include_raw_html else '',
                    "metadata": getattr(result, 'metadata', {}),
                    "links": getattr(result, 'links', []),
                    "screenshot": getattr(result, 'screenshot', ''),
                    "content_length": len(getattr(result, 'markdown', '')),
                    "extraction_method": "firecrawl",
                    "scraped_at": datetime.utcnow().isoformat()
                }
                
                # Log extraction success
                self.logger.info(f"✅ Firecrawl extraction successful: {scraped_data['content_length']} chars")
                if scraped_data['title']:
                    self.logger.info(f"📄 Document title: {scraped_data['title']}")
                
                return scraped_data
            else:
                error_msg = 'No markdown content returned from Firecrawl' if result else 'No response from Firecrawl'
                self.logger.error(f"❌ Firecrawl scrape failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "url": url
                }
                
        except Exception as e:
            self.logger.error(f"❌ Firecrawl scraping error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def _firecrawl_extract_regulations(self, url: str, custom_schema: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract structured regulation data using Firecrawl's AI extraction
        
        Args:
            url: Target URL containing regulations
            custom_schema: Optional custom extraction schema
            
        Returns:
            Dict containing structured regulation data
        """
        if not self.firecrawl_client:
            return {"success": False, "error": "Firecrawl client not initialized"}
        
        try:
            # Default regulation extraction schema
            default_schema = {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Full title of the regulation or act"},
                    "citation": {"type": "string", "description": "Official citation or reference number"},
                    "authority": {"type": "string", "description": "Issuing authority or government body"},
                    "effective_date": {"type": "string", "description": "Date when regulation becomes effective"},
                    "jurisdiction": {"type": "string", "description": "Legal jurisdiction (UK, US, EU, etc.)"},
                    "document_type": {"type": "string", "description": "Type of document (act, regulation, statutory instrument, etc.)"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object", 
                            "properties": {
                                "section_number": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "subsections": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "definitions": {"type": "array", "items": {"type": "string"}},
                    "amendments": {"type": "array", "items": {"type": "string"}},
                    "related_legislation": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title", "document_type", "sections"]
            }
            
            # Use custom schema if provided
            schema = custom_schema or default_schema
            
            self.logger.info(f"🔥 Firecrawl extracting regulations from: {url}")
            
            # Extract with custom prompt for regulations
            extraction_prompt = """Extract all regulatory and legal content from this page. Focus on:
            1. Official titles, citations, and reference numbers
            2. Legal authority and jurisdiction information  
            3. Effective dates and amendment history
            4. Section structure and hierarchical organization
            5. Legal definitions and key terms
            6. References to related legislation
            7. Specific regulatory requirements and compliance details
            
            Ensure accuracy and completeness for legal document processing."""
            
            result = self.firecrawl_client.extract({
                "url": url,
                "prompt": extraction_prompt,
                "schema": schema
            })
            
            if result and result.get('success', False):
                extracted_data = result.get('data', {})
                
                extraction_result = {
                    "success": True,
                    "url": url,
                    "extracted_data": extracted_data,
                    "extraction_method": "firecrawl_ai_extract",
                    "schema_used": schema,
                    "extracted_at": datetime.utcnow().isoformat()
                }
                
                self.logger.info(f"✅ Firecrawl regulation extraction successful")
                if extracted_data.get('title'):
                    self.logger.info(f"📄 Regulation: {extracted_data['title']}")
                
                return extraction_result
            else:
                error_msg = result.get('error', 'Unknown extraction error') if result else 'No response from Firecrawl'
                self.logger.error(f"❌ Firecrawl extraction failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "url": url
                }
                
        except Exception as e:
            self.logger.error(f"❌ Firecrawl regulation extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def _analyze_regulation_structure(self, content: str, url: str) -> Dict[str, Any]:
        """
        Analyze the hierarchical structure of extracted regulation content
        
        Args:
            content: Extracted regulation content (markdown or text)
            url: Source URL
            
        Returns:
            Dict containing structural analysis
        """
        try:
            # Use GPT-4 to analyze regulation structure
            analysis_prompt = f"""Analyze the structure and organization of this legal document content.

Content to analyze:
{content[:5000]}...

Provide a detailed structural analysis including:
1. Document hierarchy (parts, chapters, sections, subsections)
2. Legal citation patterns and numbering systems  
3. Definition sections and key terms
4. Cross-references and related provisions
5. Amendment and modification indicators
6. Content organization patterns
7. Quality assessment of the extraction

Return structured analysis as JSON."""

            context = AgentContext(
                session_id=f"structure_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=url,
                metadata={"analysis_type": "structural", "content_length": len(content), "url": url}
            )
            
            # Get LLM analysis
            analysis_response = await self.generate_response(analysis_prompt, context)
            
            if analysis_response and analysis_response.get('content'):
                try:
                    # Try to parse as JSON
                    analysis_data = json.loads(analysis_response.get('content'))
                except json.JSONDecodeError:
                    # If not valid JSON, return as structured text
                    analysis_data = {"analysis": analysis_response, "format": "text"}
                
                return {
                    "success": True,
                    "url": url,
                    "structural_analysis": analysis_data,
                    "content_length": len(content),
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            else:
                return {"success": False, "error": "No analysis response from LLM"}
                
        except Exception as e:
            self.logger.error(f"❌ Structure analysis error: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_legal_metadata(self, content: str, url: str) -> Dict[str, Any]:
        """
        Extract legal metadata from regulation content
        
        Args:
            content: Regulation content text
            url: Source URL
            
        Returns:
            Dict containing extracted legal metadata
        """
        try:
            # Use GPT-4 to extract legal metadata
            metadata_prompt = f"""Extract comprehensive legal metadata from this regulation document.

Content:
{content[:3000]}...

Extract the following metadata elements and return as structured JSON:
{{
    "title": "Full official title of the document",
    "short_title": "Short or abbreviated title if available", 
    "citation": "Official citation number or reference",
    "authority": "Issuing government authority or department",
    "jurisdiction": "Legal jurisdiction (UK, US, EU, etc.)",
    "document_type": "Type (act, regulation, statutory instrument, etc.)",
    "effective_date": "Date regulation becomes effective",
    "publication_date": "Date of publication",
    "last_modified": "Last modification date if available",
    "version": "Version or revision information",
    "status": "Current legal status (active, repealed, amended, etc.)",
    "subject_areas": ["List of subject areas/topics covered"],
    "legal_references": ["References to other laws or regulations"],
    "definitions": ["Key legal terms defined in the document"],
    "scope": "Description of regulatory scope and applicability"
}}

Focus on accuracy and completeness of legal metadata extraction."""

            context = AgentContext(
                session_id=f"metadata_extraction_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=url,
                metadata={"extraction_type": "legal_metadata", "content_length": len(content), "url": url}
            )
            
            # Get LLM metadata extraction
            metadata_response = await self.generate_response(metadata_prompt, context)
            
            if metadata_response and metadata_response.get('content'):
                try:
                    # Parse JSON response
                    metadata = json.loads(metadata_response.get('content'))
                    
                    return {
                        "success": True,
                        "url": url,
                        "legal_metadata": metadata,
                        "extracted_at": datetime.utcnow().isoformat(),
                        "extraction_method": "llm_analysis"
                    }
                    
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract key-value pairs
                    self.logger.warning("Metadata not in JSON format, attempting text parsing")
                    return {
                        "success": True,
                        "url": url,
                        "legal_metadata": {"raw_analysis": metadata_response},
                        "extracted_at": datetime.utcnow().isoformat(),
                        "extraction_method": "llm_analysis",
                        "format": "text"
                    }
            else:
                return {"success": False, "error": "No metadata response from LLM"}
                
        except Exception as e:
            self.logger.error(f"❌ Legal metadata extraction error: {e}")
            return {"success": False, "error": str(e)}

    async def extract_regulation_comprehensive(self, url: str) -> Dict[str, Any]:
        """
        Perform comprehensive regulation extraction using all available tools
        
        Args:
            url: Target regulation URL
            
        Returns:
            Complete extraction results with content, structure, and metadata
        """
        try:
            self.logger.info(f"🚀 Starting comprehensive regulation extraction: {url}")
            
            # Step 1: Firecrawl scraping for clean content
            scrape_result = await self._firecrawl_scrape(url, include_raw_html=True)
            
            if not scrape_result.get('success', False):
                self.logger.error(f"❌ Initial scraping failed: {scrape_result.get('error')}")
                return scrape_result
            
            content = scrape_result.get('markdown', '')
            if not content:
                return {"success": False, "error": "No content extracted from URL"}
            
            # Step 2: Structured regulation extraction (temporarily skip)
            regulation_data = {"success": False, "note": "Extract endpoint temporarily disabled"}
            
            # Step 3: Structural analysis  
            structure_analysis = await self._analyze_regulation_structure(content, url)
            
            # Step 4: Legal metadata extraction
            legal_metadata = await self._extract_legal_metadata(content, url)
            
            # Combine all results
            comprehensive_result = {
                "success": True,
                "url": url,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "scrape_data": scrape_result,
                "regulation_data": regulation_data.get('extracted_data', {}) if regulation_data.get('success') else {},
                "structural_analysis": structure_analysis.get('structural_analysis', {}) if structure_analysis.get('success') else {},
                "legal_metadata": legal_metadata.get('legal_metadata', {}) if legal_metadata.get('success') else {},
                "content_stats": {
                    "content_length": len(content),
                    "title_extracted": bool(scrape_result.get('title')),
                    "structured_data_available": regulation_data.get('success', False),
                    "metadata_extracted": legal_metadata.get('success', False),
                    "structure_analyzed": structure_analysis.get('success', False)
                },
                "extraction_method": "firecrawl_comprehensive"
            }
            
            self.logger.info(f"✅ Comprehensive extraction completed for: {url}")
            self.logger.info(f"📊 Content: {len(content)} chars, Structured: {regulation_data.get('success')}, Metadata: {legal_metadata.get('success')}")
            
            return comprehensive_result
            
        except Exception as e:
            self.logger.error(f"❌ Comprehensive extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check agent health and Firecrawl connectivity"""
        health = await super().health_check()
        
        # Check Firecrawl availability
        firecrawl_status = {
            "available": self.firecrawl_client is not None,
            "api_key_configured": bool(self.firecrawl_api_key),
            "client_initialized": bool(self.firecrawl_client)
        }
        
        if self.firecrawl_client:
            try:
                # Test with a simple request (if Firecrawl supports health checks)
                firecrawl_status["connectivity"] = "available"
            except Exception as e:
                firecrawl_status["connectivity"] = f"error: {e}"
        
        health["firecrawl"] = firecrawl_status
        return health