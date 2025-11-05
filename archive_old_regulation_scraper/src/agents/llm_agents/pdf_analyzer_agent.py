"""
PDF Analysis LLM Agent
GPT-4 powered agent for intelligent PDF document analysis and content extraction
"""
import asyncio
import logging
import json
import tempfile
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
import base64
from dataclasses import asdict

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...models.regulation_models import Regulation, DocumentType, LegalAuthority, DocumentMetadata
from ...models.extraction_models import ExtractedContent, WebsiteProfile, ContentQuality


class PDFAnalyzerAgent(BaseLLMAgent):
    """GPT-4 powered PDF analysis and content extraction agent"""
    
    def __init__(self, agent_id: str, broker: MessageBroker):
        system_prompt = """You are an expert PDF analysis agent specializing in extracting regulatory and legal content from PDF documents.

Your capabilities include:
- Analyzing PDF document structure and layout
- Extracting text content from both text-based and scanned PDFs
- Identifying regulatory content, legal citations, and official documents
- Processing multi-page documents with cross-references
- Handling various PDF formats including government publications
- Performing OCR on image-based PDFs
- Extracting metadata and document properties

When analyzing PDFs:
1. First assess the document type and structure
2. Extract text content using appropriate methods
3. Identify regulatory sections, articles, and provisions
4. Extract metadata like publication dates, authorities, citations
5. Assess content quality and completeness
6. Structure the extracted content according to legal document hierarchy

Always provide confidence scores and indicate which extraction method was used."""

        super().__init__(
            agent_id=agent_id,
            agent_role=AgentRole.PDF_ANALYZER,
            broker=broker,
            system_prompt=system_prompt,
            model="gpt-4-turbo-preview"
        )
    
    async def _register_tools(self):
        """Register PDF analysis tools"""
        
        # PDF document analysis tool
        self.register_tool(
            name="analyze_pdf_document",
            function=self._analyze_pdf_document,
            description="Analyze PDF document structure, metadata, and determine extraction strategy",
            parameters={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file to analyze"
                    }
                },
                "required": ["pdf_path"]
            }
        )
        
        # Text extraction tool
        self.register_tool(
            name="extract_pdf_text",
            function=self._extract_pdf_text,
            description="Extract text content from PDF using PyMuPDF",
            parameters={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    },
                    "page_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional page range to extract [start, end]"
                    }
                },
                "required": ["pdf_path"]
            }
        )
        
        # OCR extraction tool
        self.register_tool(
            name="extract_pdf_with_ocr",
            function=self._extract_pdf_with_ocr,
            description="Extract text from scanned PDFs using OCR",
            parameters={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    },
                    "page_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional page range to process [start, end]"
                    },
                    "ocr_language": {
                        "type": "string",
                        "description": "OCR language code (default: eng)",
                        "default": "eng"
                    }
                },
                "required": ["pdf_path"]
            }
        )
        
        # Regulation extraction tool
        self.register_tool(
            name="extract_regulations_from_text",
            function=self._extract_regulations_from_text,
            description="Extract structured regulation data from PDF text content",
            parameters={
                "type": "object",
                "properties": {
                    "text_content": {
                        "type": "string",
                        "description": "Raw text content from PDF"
                    },
                    "document_metadata": {
                        "type": "object",
                        "description": "PDF metadata and document information"
                    }
                },
                "required": ["text_content"]
            }
        )
        
        # Quality assessment tool
        self.register_tool(
            name="assess_pdf_extraction_quality",
            function=self._assess_pdf_extraction_quality,
            description="Assess the quality and completeness of PDF extraction",
            parameters={
                "type": "object",
                "properties": {
                    "original_pdf_info": {
                        "type": "object",
                        "description": "Original PDF document information"
                    },
                    "extracted_content": {
                        "type": "object",
                        "description": "Extracted regulation content"
                    },
                    "extraction_method": {
                        "type": "string",
                        "description": "Method used for extraction (text/ocr/hybrid)"
                    }
                },
                "required": ["original_pdf_info", "extracted_content", "extraction_method"]
            }
        )
    
    async def _handle_job_request(self, message: Message, context: AgentContext):
        """Handle PDF analysis job requests"""
        try:
            payload = message.payload
            pdf_path = payload.get("pdf_path")
            job_id = payload.get("job_id")
            
            if not pdf_path:
                raise ValueError("PDF path is required")
            
            self.logger.info(f"Processing PDF analysis job {job_id} for: {pdf_path}")
            
            # Generate analysis response
            user_message = f"""Analyze the PDF document at path: {pdf_path}

Please:
1. First analyze the document structure and properties
2. Determine the best extraction method (text extraction vs OCR)
3. Extract the content using the appropriate method
4. Extract structured regulation data from the content
5. Assess the quality of the extraction
6. Return comprehensive results with confidence scores

Document context: {json.dumps(payload, indent=2)}"""

            result = await self.generate_response(user_message, context, use_tools=True)
            
            # Send results
            await self._send_response(
                message_type=MessageType.CONTENT_EXTRACTED,
                recipient=message.sender,
                payload={
                    "job_id": job_id,
                    "agent_id": self.agent_id,
                    "pdf_path": pdf_path,
                    "analysis_result": result,
                    "timestamp": context.metadata.get("timestamp")
                },
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Error processing PDF analysis job: {e}")
            await self._send_error_response(message, str(e))
    
    async def _analyze_pdf_document(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze PDF document structure and metadata"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": f"PDF file not found: {pdf_path}"}
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = doc.metadata
            
            # Analyze document structure
            analysis = {
                "file_path": pdf_path,
                "file_size": os.path.getsize(pdf_path),
                "page_count": len(doc),
                "metadata": {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "subject": metadata.get("subject", ""),
                    "creator": metadata.get("creator", ""),
                    "producer": metadata.get("producer", ""),
                    "creation_date": metadata.get("creationDate", ""),
                    "modification_date": metadata.get("modDate", "")
                },
                "pages_analysis": [],
                "text_extractable": True,
                "estimated_language": "en",
                "document_type": "unknown"
            }
            
            # Analyze first few pages for content type detection
            text_content = ""
            images_found = 0
            
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                page_text = page.get_text()
                text_content += page_text
                
                # Check for images
                image_list = page.get_images()
                images_found += len(image_list)
                
                # Analyze page
                page_analysis = {
                    "page_number": page_num + 1,
                    "text_length": len(page_text),
                    "has_images": len(image_list) > 0,
                    "image_count": len(image_list),
                    "text_extractable": len(page_text.strip()) > 0
                }
                
                analysis["pages_analysis"].append(page_analysis)
            
            # Determine if text extraction is viable
            total_text_length = len(text_content.strip())
            analysis["text_extractable"] = total_text_length > 100
            analysis["estimated_text_length"] = total_text_length
            analysis["images_found"] = images_found
            
            # Try to classify document type based on content
            if any(keyword in text_content.lower() for keyword in 
                   ["regulation", "act", "law", "statute", "code", "ordinance", "rule"]):
                analysis["document_type"] = "regulation"
            elif any(keyword in text_content.lower() for keyword in 
                     ["policy", "procedure", "guideline", "directive"]):
                analysis["document_type"] = "policy"
            elif "government" in text_content.lower():
                analysis["document_type"] = "government"
            
            # Recommend extraction strategy
            if analysis["text_extractable"]:
                analysis["recommended_extraction"] = "text"
            else:
                analysis["recommended_extraction"] = "ocr"
            
            doc.close()
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing PDF document: {e}")
            return {"error": str(e)}
    
    async def _extract_pdf_text(self, pdf_path: str, page_range: Optional[List[int]] = None) -> Dict[str, Any]:
        """Extract text content from PDF using PyMuPDF"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": f"PDF file not found: {pdf_path}"}
            
            doc = fitz.open(pdf_path)
            
            # Determine page range
            start_page = 0
            end_page = len(doc)
            
            if page_range and len(page_range) >= 2:
                start_page = max(0, page_range[0] - 1)  # Convert to 0-based
                end_page = min(len(doc), page_range[1])
            
            # Extract text content
            extracted_text = ""
            page_contents = []
            
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text.strip():
                    extracted_text += f"\n--- Page {page_num + 1} ---\n"
                    extracted_text += page_text
                    
                    page_contents.append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "text_length": len(page_text)
                    })
            
            doc.close()
            
            return {
                "method": "text_extraction",
                "pages_processed": end_page - start_page,
                "total_text_length": len(extracted_text),
                "text_content": extracted_text,
                "page_contents": page_contents,
                "success": len(extracted_text.strip()) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting PDF text: {e}")
            return {"error": str(e)}
    
    async def _extract_pdf_with_ocr(self, pdf_path: str, page_range: Optional[List[int]] = None, ocr_language: str = "eng") -> Dict[str, Any]:
        """Extract text from PDF using OCR"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": f"PDF file not found: {pdf_path}"}
            
            doc = fitz.open(pdf_path)
            
            # Determine page range
            start_page = 0
            end_page = len(doc)
            
            if page_range and len(page_range) >= 2:
                start_page = max(0, page_range[0] - 1)
                end_page = min(len(doc), page_range[1])
            
            extracted_text = ""
            page_contents = []
            
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # Increase resolution for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                pil_image = Image.open(io.BytesIO(img_data))
                
                # Perform OCR
                try:
                    page_text = pytesseract.image_to_string(
                        pil_image, 
                        lang=ocr_language,
                        config='--psm 6'  # Assume uniform block of text
                    )
                    
                    if page_text.strip():
                        extracted_text += f"\n--- Page {page_num + 1} (OCR) ---\n"
                        extracted_text += page_text
                        
                        page_contents.append({
                            "page_number": page_num + 1,
                            "text": page_text,
                            "text_length": len(page_text),
                            "extraction_method": "ocr"
                        })
                
                except Exception as ocr_error:
                    self.logger.warning(f"OCR failed for page {page_num + 1}: {ocr_error}")
                    page_contents.append({
                        "page_number": page_num + 1,
                        "text": "",
                        "text_length": 0,
                        "extraction_method": "ocr",
                        "error": str(ocr_error)
                    })
            
            doc.close()
            
            return {
                "method": "ocr_extraction",
                "pages_processed": end_page - start_page,
                "total_text_length": len(extracted_text),
                "text_content": extracted_text,
                "page_contents": page_contents,
                "ocr_language": ocr_language,
                "success": len(extracted_text.strip()) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Error performing OCR on PDF: {e}")
            return {"error": str(e)}
    
    async def _extract_regulations_from_text(self, text_content: str, document_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract structured regulation data from PDF text content"""
        try:
            # Use GPT-4 to analyze and extract structured regulation data
            analysis_prompt = f"""Analyze this legal/regulatory document text and extract structured regulation data.

Text content:
{text_content[:8000]}{"..." if len(text_content) > 8000 else ""}

Document metadata: {json.dumps(document_metadata or {}, indent=2)}

Please extract:
1. Document title and official name
2. Legal authority/issuing body
3. Publication date and effective date
4. Document type (regulation, statute, code, etc.)
5. Jurisdiction (country, state, local)
6. Subject areas and topics covered
7. Individual regulations/sections with:
   - Section numbers/identifiers
   - Titles/headings
   - Full text content
   - Cross-references
8. Legal citations and references
9. Amendment history if present
10. Compliance requirements and deadlines

Structure the output as a comprehensive regulation document with proper hierarchy and metadata."""

            # This would typically use the LLM to process the content
            # For now, return a structured extraction template
            regulations = []
            
            # Basic text analysis to identify potential regulations
            lines = text_content.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for section markers
                if any(marker in line.lower() for marker in 
                       ['section', 'article', 'clause', 'regulation', 'rule']):
                    
                    # Save previous section
                    if current_section and current_content:
                        regulations.append({
                            "section_id": current_section,
                            "content": '\n'.join(current_content),
                            "word_count": len(' '.join(current_content).split())
                        })
                    
                    # Start new section
                    current_section = line
                    current_content = []
                else:
                    current_content.append(line)
            
            # Add final section
            if current_section and current_content:
                regulations.append({
                    "section_id": current_section,
                    "content": '\n'.join(current_content),
                    "word_count": len(' '.join(current_content).split())
                })
            
            # Extract basic metadata
            title = "Unknown Document"
            authority = "Unknown Authority"
            
            # Look for title in first few lines
            for line in text_content[:1000].split('\n'):
                if len(line.strip()) > 10 and any(word in line.lower() for word in 
                                                  ['act', 'regulation', 'code', 'law']):
                    title = line.strip()
                    break
            
            return {
                "document_title": title,
                "legal_authority": authority,
                "document_type": "regulation",
                "jurisdiction": "unknown",
                "total_regulations": len(regulations),
                "regulations": regulations,
                "extraction_method": "text_analysis",
                "confidence_score": 0.7,
                "requires_manual_review": len(regulations) == 0
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting regulations from text: {e}")
            return {"error": str(e)}
    
    async def _assess_pdf_extraction_quality(self, original_pdf_info: Dict, extracted_content: Dict, extraction_method: str) -> Dict[str, Any]:
        """Assess the quality and completeness of PDF extraction"""
        try:
            quality_score = 0.0
            issues = []
            recommendations = []
            
            # Check text extraction success
            if extracted_content.get("success", False):
                quality_score += 0.3
            else:
                issues.append("Text extraction failed or produced minimal content")
                recommendations.append("Consider trying OCR extraction for scanned documents")
            
            # Check content length vs page count
            pages_processed = extracted_content.get("pages_processed", 0)
            text_length = extracted_content.get("total_text_length", 0)
            
            if pages_processed > 0:
                avg_text_per_page = text_length / pages_processed
                if avg_text_per_page > 500:  # Good amount of text per page
                    quality_score += 0.2
                elif avg_text_per_page > 100:
                    quality_score += 0.1
                else:
                    issues.append(f"Low text density: {avg_text_per_page:.0f} chars per page")
            
            # Check extraction method appropriateness
            if extraction_method == "text" and original_pdf_info.get("text_extractable", True):
                quality_score += 0.2
            elif extraction_method == "ocr" and not original_pdf_info.get("text_extractable", True):
                quality_score += 0.2
            else:
                issues.append(f"Extraction method '{extraction_method}' may not be optimal for this document")
            
            # Check for regulation content
            if extracted_content.get("total_regulations", 0) > 0:
                quality_score += 0.3
                if extracted_content.get("total_regulations", 0) > 5:
                    quality_score += 0.1  # Bonus for comprehensive extraction
            else:
                issues.append("No structured regulations identified")
                recommendations.append("Manual review required to identify regulatory content")
            
            # Final quality assessment
            quality_level = "poor"
            if quality_score >= 0.8:
                quality_level = "excellent"
            elif quality_score >= 0.6:
                quality_level = "good"
            elif quality_score >= 0.4:
                quality_level = "fair"
            
            return {
                "quality_score": min(1.0, quality_score),
                "quality_level": quality_level,
                "extraction_method": extraction_method,
                "pages_processed": pages_processed,
                "text_extracted": text_length > 0,
                "regulations_found": extracted_content.get("total_regulations", 0),
                "issues": issues,
                "recommendations": recommendations,
                "requires_manual_review": quality_score < 0.5,
                "confidence": "high" if quality_score >= 0.7 else "medium" if quality_score >= 0.4 else "low"
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing PDF extraction quality: {e}")
            return {
                "error": str(e),
                "quality_score": 0.0,
                "quality_level": "failed"
            }