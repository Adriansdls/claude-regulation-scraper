"""
Multi-Modal Vision Processing Agent
GPT-4V powered agent for processing visual content and extracting regulatory information from images
"""
import asyncio
import logging
import json
import base64
import tempfile
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import io
import pytesseract
from datetime import datetime

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...models.regulation_models import Regulation, DocumentType, LegalAuthority
from ...models.extraction_models import ExtractedContent, ContentQuality


class VisionProcessorAgent(BaseLLMAgent):
    """GPT-4V powered multi-modal vision processing agent for regulatory content extraction"""
    
    def __init__(self, agent_id: str, broker: MessageBroker):
        system_prompt = """You are an expert multi-modal vision processing agent specializing in analyzing visual content for regulatory information extraction.

Your capabilities include:
- Analyzing images of regulatory documents, forms, and legal texts
- Processing screenshots of government websites and regulatory portals
- Extracting text and structured data from visual regulatory content
- Identifying document layouts, tables, and regulatory hierarchies
- Processing charts, diagrams, and visual regulatory information
- Handling scanned documents and image-based PDFs
- Recognizing official seals, letterheads, and document authenticity markers
- Converting visual regulatory content to structured data

When processing visual content:
1. First analyze the image for document type and layout
2. Identify text regions and regulatory content areas
3. Extract textual content using appropriate methods
4. Recognize regulatory structures (sections, subsections, lists)
5. Identify tables, forms, and structured data elements
6. Extract metadata like dates, authorities, and document numbers
7. Assess image quality and extraction confidence
8. Provide structured output with confidence scores

Always describe what you observe in the image before extracting content, and indicate confidence levels for all extractions."""

        super().__init__(
            agent_id=agent_id,
            agent_role=AgentRole.VISION_PROCESSOR,
            broker=broker,
            system_prompt=system_prompt,
            model="gpt-4-vision-preview"
        )
    
    async def _register_tools(self):
        """Register vision processing tools"""
        
        # Image analysis and description
        self.register_tool(
            name="analyze_regulatory_image",
            function=self._analyze_regulatory_image,
            description="Analyze image for regulatory content and document structure",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to analyze"
                    },
                    "analysis_focus": {
                        "type": "string",
                        "description": "Focus area: document_structure, text_extraction, form_analysis, or general",
                        "default": "general"
                    }
                },
                "required": ["image_path"]
            }
        )
        
        # Text extraction from images
        self.register_tool(
            name="extract_text_from_image",
            function=self._extract_text_from_image,
            description="Extract text content from regulatory images using OCR and vision AI",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file"
                    },
                    "preprocessing": {
                        "type": "boolean",
                        "description": "Apply image preprocessing for better OCR",
                        "default": True
                    },
                    "ocr_language": {
                        "type": "string",
                        "description": "OCR language code",
                        "default": "eng"
                    }
                },
                "required": ["image_path"]
            }
        )
        
        # Table and form extraction
        self.register_tool(
            name="extract_structured_data",
            function=self._extract_structured_data,
            description="Extract tables, forms, and structured data from regulatory images",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file"
                    },
                    "structure_type": {
                        "type": "string",
                        "description": "Expected structure: table, form, list, or mixed",
                        "default": "mixed"
                    }
                },
                "required": ["image_path"]
            }
        )
        
        # Document metadata extraction
        self.register_tool(
            name="extract_document_metadata",
            function=self._extract_document_metadata,
            description="Extract metadata from regulatory document images (dates, authorities, etc.)",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file"
                    }
                },
                "required": ["image_path"]
            }
        )
        
        # Quality assessment for visual extraction
        self.register_tool(
            name="assess_image_quality",
            function=self._assess_image_quality,
            description="Assess image quality and extraction feasibility",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file"
                    }
                },
                "required": ["image_path"]
            }
        )
        
        # Multi-page image processing
        self.register_tool(
            name="process_image_sequence",
            function=self._process_image_sequence,
            description="Process sequence of images as a single regulatory document",
            parameters={
                "type": "object",
                "properties": {
                    "image_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of image file paths in sequence"
                    },
                    "merge_content": {
                        "type": "boolean",
                        "description": "Merge extracted content into single document",
                        "default": True
                    }
                },
                "required": ["image_paths"]
            }
        )
    
    async def _handle_job_request(self, message: Message, context: AgentContext):
        """Handle vision processing job requests"""
        try:
            payload = message.payload
            job_id = payload.get("job_id")
            image_path = payload.get("image_path")
            image_paths = payload.get("image_paths", [])
            processing_type = payload.get("processing_type", "general")
            
            if not image_path and not image_paths:
                raise ValueError("Image path or paths are required")
            
            self.logger.info(f"Processing vision analysis job {job_id} for: {image_path or image_paths}")
            
            # Generate vision analysis response
            if image_paths:
                user_message = f"""Process this sequence of regulatory document images:
{json.dumps(image_paths, indent=2)}

Processing type: {processing_type}

Please:
1. Process each image in the sequence
2. Extract regulatory content and structure
3. Merge content into coherent document if applicable
4. Provide quality assessment and confidence scores"""
            else:
                user_message = f"""Analyze this regulatory document image: {image_path}

Processing type: {processing_type}

Please:
1. Analyze the image for regulatory content and structure
2. Extract text and structured data
3. Extract document metadata
4. Assess image quality and extraction confidence
5. Provide comprehensive results with confidence scores"""

            result = await self.generate_response(user_message, context, use_tools=True)
            
            # Send vision processing results
            await self._send_response(
                message_type=MessageType.CONTENT_EXTRACTED,
                recipient=message.sender,
                payload={
                    "job_id": job_id,
                    "agent_id": self.agent_id,
                    "image_path": image_path,
                    "image_paths": image_paths,
                    "vision_result": result,
                    "timestamp": datetime.utcnow().isoformat()
                },
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Error processing vision job: {e}")
            await self._send_error_response(message, str(e))
    
    async def _analyze_regulatory_image(self, image_path: str, analysis_focus: str = "general") -> Dict[str, Any]:
        """Analyze image for regulatory content and structure"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"Image file not found: {image_path}"}
            
            # Load and analyze image
            with Image.open(image_path) as img:
                # Basic image properties
                width, height = img.size
                mode = img.mode
                format_name = img.format
                
                # Convert to base64 for GPT-4V analysis
                img_base64 = await self._image_to_base64(image_path)
                
                analysis = {
                    "image_path": image_path,
                    "image_properties": {
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "format": format_name,
                        "file_size": os.path.getsize(image_path)
                    },
                    "analysis_focus": analysis_focus,
                    "document_type": "unknown",
                    "content_areas": [],
                    "text_regions": [],
                    "quality_indicators": {}
                }
                
                # Analyze image characteristics for OCR suitability
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Simple quality assessment
                is_dark = self._assess_image_darkness(img)
                has_good_contrast = self._assess_image_contrast(img)
                estimated_text_density = self._estimate_text_density(img)
                
                analysis["quality_indicators"] = {
                    "is_dark": is_dark,
                    "good_contrast": has_good_contrast,
                    "estimated_text_density": estimated_text_density,
                    "recommended_for_ocr": has_good_contrast and not is_dark and estimated_text_density > 0.1
                }
                
                # Document type classification based on visual features
                if width > height * 1.2:  # Landscape format
                    analysis["document_type"] = "form_or_table"
                elif height > width * 1.3:  # Portrait format
                    analysis["document_type"] = "text_document"
                else:
                    analysis["document_type"] = "mixed_content"
                
                # Identify potential content regions (simplified)
                if estimated_text_density > 0.3:
                    analysis["content_areas"].append({
                        "type": "text_heavy",
                        "confidence": 0.8,
                        "location": "full_document"
                    })
                
                if width > 1000 and height > 800:  # High resolution
                    analysis["quality_indicators"]["high_resolution"] = True
                    analysis["extraction_confidence"] = 0.8
                else:
                    analysis["quality_indicators"]["high_resolution"] = False
                    analysis["extraction_confidence"] = 0.6
                
                return analysis
        
        except Exception as e:
            self.logger.error(f"Error analyzing regulatory image: {e}")
            return {"error": str(e)}
    
    async def _extract_text_from_image(self, image_path: str, preprocessing: bool = True, ocr_language: str = "eng") -> Dict[str, Any]:
        """Extract text from regulatory images using OCR"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"Image file not found: {image_path}"}
            
            # Load image
            with Image.open(image_path) as img:
                processed_img = img.copy()
                
                # Apply preprocessing if requested
                if preprocessing:
                    processed_img = await self._preprocess_image_for_ocr(processed_img)
                
                # Extract text using pytesseract
                ocr_text = pytesseract.image_to_string(
                    processed_img,
                    lang=ocr_language,
                    config='--psm 6'  # Assume uniform block of text
                )
                
                # Extract detailed information with bounding boxes
                ocr_data = pytesseract.image_to_data(
                    processed_img,
                    output_type=pytesseract.Output.DICT,
                    lang=ocr_language
                )
                
                # Process OCR results
                words = []
                lines = []
                current_line = []
                current_line_num = -1
                
                for i in range(len(ocr_data['text'])):
                    if int(ocr_data['conf'][i]) > 0:  # Valid detection
                        word_info = {
                            'text': ocr_data['text'][i],
                            'confidence': int(ocr_data['conf'][i]),
                            'bbox': {
                                'x': ocr_data['left'][i],
                                'y': ocr_data['top'][i],
                                'width': ocr_data['width'][i],
                                'height': ocr_data['height'][i]
                            },
                            'line_num': ocr_data['line_num'][i]
                        }
                        
                        words.append(word_info)
                        
                        # Group words by line
                        if ocr_data['line_num'][i] != current_line_num:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = []
                            current_line_num = ocr_data['line_num'][i]
                        
                        current_line.append(ocr_data['text'][i])
                
                # Add final line
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Calculate extraction statistics
                total_words = len([w for w in words if w['text'].strip()])
                high_conf_words = len([w for w in words if w['confidence'] > 80])
                avg_confidence = sum(w['confidence'] for w in words) / len(words) if words else 0
                
                return {
                    "method": "ocr_extraction",
                    "preprocessing_applied": preprocessing,
                    "ocr_language": ocr_language,
                    "extracted_text": ocr_text,
                    "text_lines": lines,
                    "word_details": words,
                    "statistics": {
                        "total_characters": len(ocr_text),
                        "total_words": total_words,
                        "high_confidence_words": high_conf_words,
                        "average_confidence": avg_confidence,
                        "extraction_quality": "good" if avg_confidence > 70 else "fair" if avg_confidence > 50 else "poor"
                    },
                    "success": len(ocr_text.strip()) > 0
                }
        
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return {"error": str(e)}
    
    async def _extract_structured_data(self, image_path: str, structure_type: str = "mixed") -> Dict[str, Any]:
        """Extract structured data (tables, forms) from images"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"Image file not found: {image_path}"}
            
            # First extract all text to analyze structure
            text_result = await self._extract_text_from_image(image_path, preprocessing=True)
            
            if text_result.get("error"):
                return text_result
            
            extracted_text = text_result.get("extracted_text", "")
            word_details = text_result.get("word_details", [])
            
            structured_data = {
                "structure_type": structure_type,
                "tables": [],
                "forms": [],
                "lists": [],
                "key_value_pairs": []
            }
            
            # Analyze text for structured content patterns
            lines = extracted_text.split('\n')
            
            # Look for table-like structures
            potential_tables = []
            for i, line in enumerate(lines):
                # Simple table detection - lines with multiple columns separated by spaces
                if len(line.strip()) > 10:
                    parts = [part.strip() for part in line.split() if part.strip()]
                    if len(parts) >= 3:  # Potential table row
                        potential_tables.append({
                            "line_number": i,
                            "content": line.strip(),
                            "columns": parts,
                            "column_count": len(parts)
                        })
            
            if potential_tables:
                structured_data["tables"] = [{
                    "table_id": 1,
                    "rows": potential_tables,
                    "estimated_columns": max(row["column_count"] for row in potential_tables),
                    "confidence": 0.7
                }]
            
            # Look for form-like structures (key: value patterns)
            form_fields = []
            for line in lines:
                # Look for colon-separated key-value pairs
                if ':' in line and len(line.strip()) > 5:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if len(key) > 0 and len(key) < 50:  # Reasonable field name length
                            form_fields.append({
                                "field_name": key,
                                "field_value": value,
                                "confidence": 0.8
                            })
            
            if form_fields:
                structured_data["forms"] = [{
                    "form_id": 1,
                    "fields": form_fields,
                    "field_count": len(form_fields)
                }]
            
            # Look for numbered or bulleted lists
            list_items = []
            for line in lines:
                line = line.strip()
                # Check for numbered items (1., 2., etc.) or bullets (•, -, *)
                if re.match(r'^(\d+\.|\d+\)|\•|\-|\*|\u2022)', line):
                    list_items.append({
                        "item_text": line,
                        "item_number": len(list_items) + 1
                    })
            
            if list_items:
                structured_data["lists"] = [{
                    "list_id": 1,
                    "items": list_items,
                    "item_count": len(list_items),
                    "list_type": "numbered" if any(re.match(r'^\d+', item["item_text"]) for item in list_items) else "bulleted"
                }]
            
            # Overall structure assessment
            structure_score = 0
            if structured_data["tables"]:
                structure_score += 0.3
            if structured_data["forms"]:
                structure_score += 0.3
            if structured_data["lists"]:
                structure_score += 0.2
            
            structured_data["extraction_summary"] = {
                "structure_score": structure_score,
                "tables_found": len(structured_data["tables"]),
                "forms_found": len(structured_data["forms"]),
                "lists_found": len(structured_data["lists"]),
                "extraction_quality": "good" if structure_score > 0.5 else "fair" if structure_score > 0.2 else "poor"
            }
            
            return structured_data
        
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {e}")
            return {"error": str(e)}
    
    async def _extract_document_metadata(self, image_path: str) -> Dict[str, Any]:
        """Extract metadata from regulatory document images"""
        try:
            # Extract text first
            text_result = await self._extract_text_from_image(image_path)
            if text_result.get("error"):
                return text_result
            
            extracted_text = text_result.get("extracted_text", "")
            
            metadata = {
                "document_title": None,
                "issuing_authority": None,
                "document_date": None,
                "document_number": None,
                "effective_date": None,
                "document_type": None,
                "jurisdiction": None,
                "signatures": [],
                "seals_detected": False
            }
            
            # Look for dates
            import re
            date_patterns = [
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
                r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # MM-DD-YYYY
                r'\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b',  # Month DD, YYYY
                r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b'   # DD Month YYYY
            ]
            
            dates_found = []
            for pattern in date_patterns:
                matches = re.findall(pattern, extracted_text)
                dates_found.extend(matches)
            
            if dates_found:
                metadata["document_date"] = dates_found[0]
                if len(dates_found) > 1:
                    metadata["effective_date"] = dates_found[1]
            
            # Look for document numbers
            doc_number_patterns = [
                r'\b(?:No\.?|Number|#)\s*([A-Z0-9-]+)\b',
                r'\b([A-Z]{2,4}-\d{2,6})\b',
                r'\bDocument\s+(?:No\.?|Number)\s*:?\s*([A-Z0-9-]+)\b'
            ]
            
            for pattern in doc_number_patterns:
                matches = re.findall(pattern, extracted_text, re.IGNORECASE)
                if matches:
                    metadata["document_number"] = matches[0]
                    break
            
            # Look for authorities/agencies
            authority_keywords = [
                "department", "agency", "commission", "board", "authority", 
                "ministry", "bureau", "office", "administration"
            ]
            
            lines = extracted_text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if any(keyword in line.lower() for keyword in authority_keywords) and len(line) > 10:
                    metadata["issuing_authority"] = line
                    break
            
            # Look for document type indicators
            doc_type_keywords = {
                "regulation": ["regulation", "rule", "code"],
                "statute": ["statute", "act", "law"],
                "policy": ["policy", "procedure", "guideline"],
                "form": ["form", "application", "request"]
            }
            
            for doc_type, keywords in doc_type_keywords.items():
                if any(keyword in extracted_text.lower() for keyword in keywords):
                    metadata["document_type"] = doc_type
                    break
            
            # Look for titles (typically in first few lines, may be in caps or bold)
            for line in lines[:5]:
                line = line.strip()
                if len(line) > 10 and len(line) < 100:
                    # Check if line looks like a title
                    if (line.isupper() or 
                        any(word in line.lower() for word in ["act", "regulation", "code", "law", "policy"])):
                        metadata["document_title"] = line
                        break
            
            # Simple signature detection
            signature_indicators = ["signature", "signed", "authorized by", "approved by"]
            for indicator in signature_indicators:
                if indicator in extracted_text.lower():
                    metadata["signatures"].append({
                        "type": "detected",
                        "indicator": indicator,
                        "confidence": 0.6
                    })
            
            # Confidence assessment
            confidence_factors = 0
            if metadata["document_date"]:
                confidence_factors += 1
            if metadata["issuing_authority"]:
                confidence_factors += 1
            if metadata["document_type"]:
                confidence_factors += 1
            if metadata["document_title"]:
                confidence_factors += 1
            
            metadata["extraction_confidence"] = confidence_factors / 4.0
            metadata["metadata_completeness"] = f"{confidence_factors}/4 key fields extracted"
            
            return metadata
        
        except Exception as e:
            self.logger.error(f"Error extracting document metadata: {e}")
            return {"error": str(e)}
    
    async def _assess_image_quality(self, image_path: str) -> Dict[str, Any]:
        """Assess image quality for text extraction"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"Image file not found: {image_path}"}
            
            with Image.open(image_path) as img:
                width, height = img.size
                
                quality_assessment = {
                    "image_path": image_path,
                    "resolution": {
                        "width": width,
                        "height": height,
                        "total_pixels": width * height
                    },
                    "quality_factors": {},
                    "recommendations": []
                }
                
                # Resolution assessment
                if width >= 1200 and height >= 800:
                    quality_assessment["quality_factors"]["resolution"] = "excellent"
                elif width >= 800 and height >= 600:
                    quality_assessment["quality_factors"]["resolution"] = "good"
                else:
                    quality_assessment["quality_factors"]["resolution"] = "poor"
                    quality_assessment["recommendations"].append("Consider using higher resolution image")
                
                # Convert to RGB for analysis
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Assess darkness
                is_dark = self._assess_image_darkness(img)
                quality_assessment["quality_factors"]["brightness"] = "poor" if is_dark else "good"
                if is_dark:
                    quality_assessment["recommendations"].append("Image appears too dark, consider brightness adjustment")
                
                # Assess contrast
                has_good_contrast = self._assess_image_contrast(img)
                quality_assessment["quality_factors"]["contrast"] = "good" if has_good_contrast else "poor"
                if not has_good_contrast:
                    quality_assessment["recommendations"].append("Low contrast detected, consider contrast enhancement")
                
                # Estimate text density
                text_density = self._estimate_text_density(img)
                quality_assessment["quality_factors"]["text_density"] = text_density
                
                if text_density > 0.3:
                    quality_assessment["quality_factors"]["text_content"] = "high"
                elif text_density > 0.1:
                    quality_assessment["quality_factors"]["text_content"] = "moderate"
                else:
                    quality_assessment["quality_factors"]["text_content"] = "low"
                    quality_assessment["recommendations"].append("Low text density detected, may not be a text document")
                
                # Overall quality score
                score_factors = {
                    "excellent": 1.0, "good": 0.7, "moderate": 0.5, "poor": 0.3, "low": 0.2, "high": 0.8
                }
                
                scores = []
                for factor, rating in quality_assessment["quality_factors"].items():
                    if rating in score_factors:
                        scores.append(score_factors[rating])
                    elif isinstance(rating, (int, float)):
                        scores.append(min(1.0, rating))
                
                overall_score = sum(scores) / len(scores) if scores else 0.5
                quality_assessment["overall_quality_score"] = overall_score
                
                if overall_score >= 0.8:
                    quality_assessment["overall_rating"] = "excellent"
                    quality_assessment["extraction_feasibility"] = "very_high"
                elif overall_score >= 0.6:
                    quality_assessment["overall_rating"] = "good"
                    quality_assessment["extraction_feasibility"] = "high"
                elif overall_score >= 0.4:
                    quality_assessment["overall_rating"] = "fair"
                    quality_assessment["extraction_feasibility"] = "moderate"
                else:
                    quality_assessment["overall_rating"] = "poor"
                    quality_assessment["extraction_feasibility"] = "low"
                    quality_assessment["recommendations"].append("Consider image preprocessing or using alternative extraction method")
                
                return quality_assessment
        
        except Exception as e:
            self.logger.error(f"Error assessing image quality: {e}")
            return {"error": str(e)}
    
    async def _process_image_sequence(self, image_paths: List[str], merge_content: bool = True) -> Dict[str, Any]:
        """Process sequence of images as single document"""
        try:
            if not image_paths:
                return {"error": "No image paths provided"}
            
            sequence_results = []
            all_text_content = []
            total_extraction_time = 0
            
            for i, image_path in enumerate(image_paths):
                if not os.path.exists(image_path):
                    sequence_results.append({
                        "page_number": i + 1,
                        "image_path": image_path,
                        "error": f"Image file not found: {image_path}"
                    })
                    continue
                
                # Process each image
                start_time = datetime.utcnow()
                
                # Extract text
                text_result = await self._extract_text_from_image(image_path)
                
                # Extract metadata
                metadata_result = await self._extract_document_metadata(image_path)
                
                # Assess quality
                quality_result = await self._assess_image_quality(image_path)
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                total_extraction_time += processing_time
                
                page_result = {
                    "page_number": i + 1,
                    "image_path": image_path,
                    "text_extraction": text_result,
                    "metadata": metadata_result,
                    "quality_assessment": quality_result,
                    "processing_time": processing_time
                }
                
                sequence_results.append(page_result)
                
                # Collect text content
                if not text_result.get("error") and text_result.get("extracted_text"):
                    all_text_content.append(f"--- Page {i + 1} ---\n{text_result['extracted_text']}")
            
            # Merge results if requested
            merged_result = {
                "total_pages": len(image_paths),
                "pages_processed": len([r for r in sequence_results if not r.get("error")]),
                "processing_time": total_extraction_time,
                "individual_pages": sequence_results
            }
            
            if merge_content and all_text_content:
                merged_text = "\n\n".join(all_text_content)
                merged_result["merged_content"] = {
                    "full_text": merged_text,
                    "total_characters": len(merged_text),
                    "total_words": len(merged_text.split()),
                    "pages_with_content": len(all_text_content)
                }
                
                # Extract overall metadata from merged content
                overall_metadata = await self._extract_document_metadata_from_text(merged_text)
                merged_result["document_metadata"] = overall_metadata
            
            # Calculate success metrics
            successful_pages = len([r for r in sequence_results if not r.get("error")])
            merged_result["success_rate"] = successful_pages / len(image_paths) if image_paths else 0
            merged_result["extraction_quality"] = "excellent" if merged_result["success_rate"] > 0.9 else "good" if merged_result["success_rate"] > 0.7 else "fair"
            
            return merged_result
        
        except Exception as e:
            self.logger.error(f"Error processing image sequence: {e}")
            return {"error": str(e)}
    
    # Helper methods for image analysis
    async def _image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def _preprocess_image_for_ocr(self, img: Image.Image) -> Image.Image:
        """Apply preprocessing to improve OCR accuracy"""
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Apply slight sharpening
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        
        return img
    
    def _assess_image_darkness(self, img: Image.Image) -> bool:
        """Assess if image is too dark"""
        import numpy as np
        img_array = np.array(img.convert('L'))
        mean_brightness = np.mean(img_array)
        return mean_brightness < 80  # Threshold for "dark" image
    
    def _assess_image_contrast(self, img: Image.Image) -> bool:
        """Assess if image has good contrast"""
        import numpy as np
        img_array = np.array(img.convert('L'))
        std_dev = np.std(img_array)
        return std_dev > 30  # Threshold for good contrast
    
    def _estimate_text_density(self, img: Image.Image) -> float:
        """Estimate text density in image"""
        # Simple edge detection to estimate text regions
        try:
            edges = img.convert('L').filter(ImageFilter.FIND_EDGES)
            import numpy as np
            edge_array = np.array(edges)
            edge_pixels = np.sum(edge_array > 50)  # Threshold for edge detection
            total_pixels = edge_array.size
            return edge_pixels / total_pixels
        except:
            return 0.5  # Default estimate
    
    async def _extract_document_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """Extract metadata from combined text content"""
        # This is a simplified version of the metadata extraction
        # In practice, you might want to use the same logic as _extract_document_metadata
        # but adapted for plain text input
        
        metadata = {
            "total_length": len(text),
            "word_count": len(text.split()),
            "line_count": len(text.split('\n')),
            "contains_regulatory_language": False
        }
        
        # Check for regulatory language
        regulatory_terms = ["regulation", "section", "clause", "statute", "law", "code"]
        metadata["contains_regulatory_language"] = any(term in text.lower() for term in regulatory_terms)
        
        return metadata