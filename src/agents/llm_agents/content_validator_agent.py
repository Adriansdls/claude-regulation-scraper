"""
Content Validation LLM Agent
GPT-4 powered agent for validating and assessing extracted regulatory content quality
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import asdict
import re
from difflib import SequenceMatcher

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...models.regulation_models import Regulation, DocumentType, LegalAuthority, DocumentMetadata
from ...models.extraction_models import ExtractedContent, ContentQuality, ValidationResult


class ContentValidatorAgent(BaseLLMAgent):
    """GPT-4 powered content validation and quality assessment agent"""
    
    def __init__(self, agent_id: str, broker: MessageBroker):
        system_prompt = """You are an expert content validation agent specializing in assessing the quality, accuracy, and completeness of extracted regulatory content.

Your capabilities include:
- Validating extracted regulation content for accuracy and completeness
- Cross-referencing multiple extraction sources for consistency
- Detecting extraction errors, formatting issues, and missing content
- Assessing legal citation accuracy and references
- Evaluating content structure and hierarchical organization
- Identifying potential compliance issues and regulatory gaps
- Providing confidence scores and quality metrics
- Recommending content improvements and corrections

When validating content:
1. Assess completeness against original source indicators
2. Validate legal citations and cross-references
3. Check for structural integrity and proper formatting
4. Identify any extraction artifacts or errors
5. Evaluate semantic coherence and logical flow
6. Compare against regulatory document standards
7. Provide detailed quality metrics and recommendations

Always provide specific, actionable feedback with confidence levels and evidence-based assessments."""

        super().__init__(
            agent_id=agent_id,
            agent_role=AgentRole.CONTENT_VALIDATOR,
            broker=broker,
            system_prompt=system_prompt,
            model="gpt-4-turbo-preview"
        )
    
    async def _register_tools(self):
        """Register content validation tools"""
        
        # Content completeness validation
        self.register_tool(
            name="validate_content_completeness",
            function=self._validate_content_completeness,
            description="Validate completeness of extracted content against original source indicators",
            parameters={
                "type": "object",
                "properties": {
                    "extracted_content": {
                        "type": "object",
                        "description": "Extracted regulation content to validate"
                    },
                    "source_metadata": {
                        "type": "object",
                        "description": "Original source metadata and indicators"
                    }
                },
                "required": ["extracted_content", "source_metadata"]
            }
        )
        
        # Legal citation validation
        self.register_tool(
            name="validate_legal_citations",
            function=self._validate_legal_citations,
            description="Validate accuracy and format of legal citations and references",
            parameters={
                "type": "object",
                "properties": {
                    "content_text": {
                        "type": "string",
                        "description": "Text content containing citations to validate"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Legal jurisdiction for citation format standards"
                    }
                },
                "required": ["content_text"]
            }
        )
        
        # Structure and formatting validation
        self.register_tool(
            name="validate_content_structure",
            function=self._validate_content_structure,
            description="Validate hierarchical structure and formatting of regulatory content",
            parameters={
                "type": "object",
                "properties": {
                    "regulations": {
                        "type": "array",
                        "description": "List of regulation objects to validate structure"
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Expected document type (regulation, statute, code, etc.)"
                    }
                },
                "required": ["regulations"]
            }
        )
        
        # Cross-source consistency check
        self.register_tool(
            name="check_extraction_consistency",
            function=self._check_extraction_consistency,
            description="Compare multiple extraction results for consistency and identify discrepancies",
            parameters={
                "type": "object",
                "properties": {
                    "primary_extraction": {
                        "type": "object",
                        "description": "Primary extraction result to validate"
                    },
                    "secondary_extractions": {
                        "type": "array",
                        "description": "Additional extraction results for comparison"
                    }
                },
                "required": ["primary_extraction"]
            }
        )
        
        # Semantic coherence validation
        self.register_tool(
            name="validate_semantic_coherence",
            function=self._validate_semantic_coherence,
            description="Assess semantic coherence and logical flow of extracted content",
            parameters={
                "type": "object",
                "properties": {
                    "content_sections": {
                        "type": "array",
                        "description": "Content sections to analyze for coherence"
                    },
                    "regulatory_domain": {
                        "type": "string",
                        "description": "Regulatory domain context (healthcare, finance, etc.)"
                    }
                },
                "required": ["content_sections"]
            }
        )
        
        # Quality scoring and assessment
        self.register_tool(
            name="generate_quality_assessment",
            function=self._generate_quality_assessment,
            description="Generate comprehensive quality assessment with scores and recommendations",
            parameters={
                "type": "object",
                "properties": {
                    "validation_results": {
                        "type": "object",
                        "description": "Combined validation results from all checks"
                    },
                    "extraction_metadata": {
                        "type": "object",
                        "description": "Metadata about extraction process and methods"
                    }
                },
                "required": ["validation_results"]
            }
        )
    
    async def _handle_job_request(self, message: Message, context: AgentContext):
        """Handle content validation job requests"""
        try:
            payload = message.payload
            job_id = payload.get("job_id")
            extracted_content = payload.get("extracted_content")
            source_metadata = payload.get("source_metadata", {})
            
            if not extracted_content:
                raise ValueError("Extracted content is required for validation")
            
            self.logger.info(f"Processing content validation job {job_id}")
            
            # Generate validation response
            user_message = f"""Validate the extracted regulatory content for quality, accuracy, and completeness.

Extracted Content:
{json.dumps(extracted_content, indent=2)[:3000]}{"..." if len(json.dumps(extracted_content, indent=2)) > 3000 else ""}

Source Metadata:
{json.dumps(source_metadata, indent=2)}

Please perform comprehensive validation:
1. Check content completeness against source indicators
2. Validate legal citations and references
3. Assess structural integrity and formatting
4. Check for semantic coherence
5. Generate overall quality assessment with recommendations

Provide detailed feedback with confidence scores and specific improvement suggestions."""

            result = await self.generate_response(user_message, context, use_tools=True)
            
            # Send validation results
            await self._send_response(
                message_type=MessageType.CONTENT_VALIDATED,
                recipient=message.sender,
                payload={
                    "job_id": job_id,
                    "agent_id": self.agent_id,
                    "validation_result": result,
                    "timestamp": datetime.utcnow().isoformat()
                },
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Error processing content validation job: {e}")
            await self._send_error_response(message, str(e))
    
    async def _validate_content_completeness(self, extracted_content: Dict, source_metadata: Dict) -> Dict[str, Any]:
        """Validate completeness of extracted content"""
        try:
            completeness_issues = []
            completeness_score = 1.0
            
            # Check basic content requirements
            regulations = extracted_content.get("regulations", [])
            if not regulations:
                completeness_issues.append("No regulations extracted from source")
                completeness_score -= 0.5
            
            # Check against source page indicators
            source_pages = source_metadata.get("page_count", 0)
            if source_pages > 0:
                extracted_pages = len([r for r in regulations if r.get("content")])
                coverage_ratio = extracted_pages / source_pages if source_pages > 0 else 0
                
                if coverage_ratio < 0.3:
                    completeness_issues.append(f"Low page coverage: {coverage_ratio:.2%} of source pages")
                    completeness_score -= 0.3
                elif coverage_ratio < 0.7:
                    completeness_issues.append(f"Moderate page coverage: {coverage_ratio:.2%} of source pages")
                    completeness_score -= 0.1
            
            # Check for expected document sections
            expected_sections = ["title", "authority", "effective_date", "content"]
            missing_sections = []
            
            for regulation in regulations[:5]:  # Check first 5 regulations
                for section in expected_sections:
                    if not regulation.get(section):
                        missing_sections.append(f"Missing {section} in regulation")
            
            if missing_sections:
                unique_issues = list(set(missing_sections))
                completeness_issues.extend(unique_issues[:3])  # Limit to 3 unique issues
                completeness_score -= min(0.2, len(unique_issues) * 0.05)
            
            # Check content length indicators
            total_content_length = sum(len(str(r.get("content", ""))) for r in regulations)
            if total_content_length < 1000:
                completeness_issues.append("Extracted content appears incomplete (very short)")
                completeness_score -= 0.2
            
            completeness_score = max(0.0, completeness_score)
            
            return {
                "completeness_score": completeness_score,
                "completeness_level": self._get_quality_level(completeness_score),
                "total_regulations": len(regulations),
                "total_content_length": total_content_length,
                "issues": completeness_issues,
                "recommendations": self._get_completeness_recommendations(completeness_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error validating content completeness: {e}")
            return {"error": str(e)}
    
    async def _validate_legal_citations(self, content_text: str, jurisdiction: Optional[str] = None) -> Dict[str, Any]:
        """Validate legal citations and references"""
        try:
            citation_patterns = [
                r'\b\d+\s+U\.S\.C\.?\s+§?\s*\d+',  # USC citations
                r'\b\d+\s+C\.F\.R\.?\s+§?\s*\d+',  # CFR citations
                r'\bSection\s+\d+',                 # Section references
                r'\bAct\s+of\s+\d{4}',             # Act references
                r'\b\d+\s+Stat\.?\s+\d+',          # Statutes at Large
            ]
            
            citations_found = []
            citation_issues = []
            
            for pattern in citation_patterns:
                matches = re.findall(pattern, content_text, re.IGNORECASE)
                citations_found.extend(matches)
            
            # Validate citation format
            for citation in citations_found:
                if not re.search(r'\d+', citation):
                    citation_issues.append(f"Invalid citation format: {citation}")
            
            # Check for broken cross-references
            internal_refs = re.findall(r'(?:see|refer to|pursuant to)\s+(?:Section|Article|Clause)\s+(\w+)', 
                                     content_text, re.IGNORECASE)
            
            for ref in internal_refs:
                # Check if referenced section exists in content
                if not re.search(rf'Section\s+{re.escape(ref)}', content_text, re.IGNORECASE):
                    citation_issues.append(f"Broken internal reference: Section {ref}")
            
            citation_score = 1.0 - (len(citation_issues) * 0.1)
            citation_score = max(0.0, citation_score)
            
            return {
                "citation_score": citation_score,
                "citations_found": len(citations_found),
                "citation_examples": citations_found[:5],
                "internal_references": len(internal_refs),
                "issues": citation_issues,
                "recommendations": self._get_citation_recommendations(citation_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error validating legal citations: {e}")
            return {"error": str(e)}
    
    async def _validate_content_structure(self, regulations: List[Dict], document_type: Optional[str] = None) -> Dict[str, Any]:
        """Validate content structure and formatting"""
        try:
            structure_issues = []
            structure_score = 1.0
            
            if not regulations:
                return {
                    "structure_score": 0.0,
                    "issues": ["No regulations to validate structure"],
                    "recommendations": ["Verify extraction process captured regulation content"]
                }
            
            # Check for required fields
            required_fields = ["section_id", "content"]
            for i, regulation in enumerate(regulations):
                for field in required_fields:
                    if not regulation.get(field):
                        structure_issues.append(f"Regulation {i+1}: Missing {field}")
                        structure_score -= 0.05
            
            # Check section numbering consistency
            section_ids = [r.get("section_id", "") for r in regulations if r.get("section_id")]
            if section_ids:
                # Look for numbering patterns
                numeric_sections = [s for s in section_ids if re.search(r'\d+', s)]
                if len(numeric_sections) > 1:
                    # Check for sequential numbering
                    numbers = []
                    for section in numeric_sections:
                        match = re.search(r'(\d+)', section)
                        if match:
                            numbers.append(int(match.group(1)))
                    
                    if numbers and len(set(numbers)) != len(numbers):
                        structure_issues.append("Duplicate section numbers found")
                        structure_score -= 0.1
            
            # Check content length consistency
            content_lengths = [len(str(r.get("content", ""))) for r in regulations]
            if content_lengths:
                avg_length = sum(content_lengths) / len(content_lengths)
                very_short = [l for l in content_lengths if l < avg_length * 0.1]
                if len(very_short) > len(content_lengths) * 0.2:
                    structure_issues.append("Many sections have unusually short content")
                    structure_score -= 0.1
            
            structure_score = max(0.0, structure_score)
            
            return {
                "structure_score": structure_score,
                "structure_level": self._get_quality_level(structure_score),
                "total_sections": len(regulations),
                "sections_with_ids": len([r for r in regulations if r.get("section_id")]),
                "average_content_length": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
                "issues": structure_issues,
                "recommendations": self._get_structure_recommendations(structure_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error validating content structure: {e}")
            return {"error": str(e)}
    
    async def _check_extraction_consistency(self, primary_extraction: Dict, secondary_extractions: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Check consistency across multiple extractions"""
        try:
            if not secondary_extractions:
                return {
                    "consistency_score": 1.0,
                    "message": "No secondary extractions to compare"
                }
            
            consistency_issues = []
            consistency_score = 1.0
            
            primary_regs = primary_extraction.get("regulations", [])
            primary_count = len(primary_regs)
            
            # Compare regulation counts
            for i, secondary in enumerate(secondary_extractions):
                secondary_regs = secondary.get("regulations", [])
                secondary_count = len(secondary_regs)
                
                count_diff = abs(primary_count - secondary_count)
                if count_diff > primary_count * 0.2:  # More than 20% difference
                    consistency_issues.append(f"Extraction {i+1}: Significant count difference ({count_diff} regulations)")
                    consistency_score -= 0.2
            
            # Compare content similarity for matching sections
            if primary_regs and secondary_extractions:
                secondary_regs = secondary_extractions[0].get("regulations", [])
                if secondary_regs:
                    # Compare first few regulations for content similarity
                    for i in range(min(3, len(primary_regs), len(secondary_regs))):
                        primary_content = str(primary_regs[i].get("content", ""))
                        secondary_content = str(secondary_regs[i].get("content", ""))
                        
                        similarity = SequenceMatcher(None, primary_content, secondary_content).ratio()
                        if similarity < 0.7:  # Less than 70% similar
                            consistency_issues.append(f"Regulation {i+1}: Low content similarity ({similarity:.2%})")
                            consistency_score -= 0.1
            
            consistency_score = max(0.0, consistency_score)
            
            return {
                "consistency_score": consistency_score,
                "consistency_level": self._get_quality_level(consistency_score),
                "extractions_compared": len(secondary_extractions) + 1,
                "issues": consistency_issues,
                "recommendations": self._get_consistency_recommendations(consistency_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error checking extraction consistency: {e}")
            return {"error": str(e)}
    
    async def _validate_semantic_coherence(self, content_sections: List[Dict], regulatory_domain: Optional[str] = None) -> Dict[str, Any]:
        """Validate semantic coherence of content"""
        try:
            coherence_issues = []
            coherence_score = 1.0
            
            if not content_sections:
                return {
                    "coherence_score": 0.0,
                    "issues": ["No content sections to analyze"],
                    "recommendations": ["Verify content extraction captured meaningful sections"]
                }
            
            # Check for logical flow between sections
            for i in range(len(content_sections) - 1):
                current_section = content_sections[i]
                next_section = content_sections[i + 1]
                
                current_content = str(current_section.get("content", ""))
                next_content = str(next_section.get("content", ""))
                
                # Check for abrupt content changes
                if len(current_content) > 100 and len(next_content) > 100:
                    # Simple coherence check based on common words
                    current_words = set(current_content.lower().split()[:50])
                    next_words = set(next_content.lower().split()[:50])
                    
                    common_words = current_words.intersection(next_words)
                    coherence_ratio = len(common_words) / max(len(current_words), len(next_words))
                    
                    if coherence_ratio < 0.1:  # Very few common words
                        coherence_issues.append(f"Sections {i+1}-{i+2}: Low semantic coherence")
                        coherence_score -= 0.05
            
            # Check for regulatory language patterns
            regulatory_terms = [
                "shall", "must", "required", "prohibited", "permitted", "authorized",
                "compliance", "violation", "penalty", "enforcement", "regulation"
            ]
            
            sections_with_reg_terms = 0
            for section in content_sections:
                content = str(section.get("content", "")).lower()
                if any(term in content for term in regulatory_terms):
                    sections_with_reg_terms += 1
            
            reg_term_ratio = sections_with_reg_terms / len(content_sections)
            if reg_term_ratio < 0.3:  # Less than 30% of sections have regulatory terms
                coherence_issues.append("Content may not be regulatory in nature")
                coherence_score -= 0.2
            
            coherence_score = max(0.0, coherence_score)
            
            return {
                "coherence_score": coherence_score,
                "coherence_level": self._get_quality_level(coherence_score),
                "sections_analyzed": len(content_sections),
                "regulatory_language_ratio": reg_term_ratio,
                "issues": coherence_issues,
                "recommendations": self._get_coherence_recommendations(coherence_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error validating semantic coherence: {e}")
            return {"error": str(e)}
    
    async def _generate_quality_assessment(self, validation_results: Dict, extraction_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate comprehensive quality assessment"""
        try:
            # Collect scores from validation results
            scores = {}
            issues = []
            recommendations = []
            
            for key, result in validation_results.items():
                if isinstance(result, dict) and not result.get("error"):
                    # Extract score
                    score_key = f"{key.replace('_result', '')}_score"
                    if score_key in result:
                        scores[key] = result[score_key]
                    
                    # Collect issues and recommendations
                    if result.get("issues"):
                        issues.extend(result["issues"])
                    if result.get("recommendations"):
                        recommendations.extend(result["recommendations"])
            
            # Calculate overall quality score
            if scores:
                overall_score = sum(scores.values()) / len(scores)
            else:
                overall_score = 0.0
            
            # Determine quality level and confidence
            quality_level = self._get_quality_level(overall_score)
            confidence = "high" if overall_score >= 0.8 else "medium" if overall_score >= 0.5 else "low"
            
            # Generate summary
            summary = self._generate_quality_summary(overall_score, len(issues), extraction_metadata)
            
            return {
                "overall_quality_score": overall_score,
                "quality_level": quality_level,
                "confidence": confidence,
                "component_scores": scores,
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if any(term in i.lower() 
                                                               for term in ["missing", "failed", "broken"])]),
                "issues": issues[:10],  # Limit to top 10 issues
                "recommendations": list(set(recommendations[:10])),  # Unique top 10 recommendations
                "summary": summary,
                "validation_timestamp": datetime.utcnow().isoformat(),
                "requires_manual_review": overall_score < 0.6 or len(issues) > 5
            }
            
        except Exception as e:
            self.logger.error(f"Error generating quality assessment: {e}")
            return {"error": str(e)}
    
    def _get_quality_level(self, score: float) -> str:
        """Convert numeric score to quality level"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        elif score >= 0.3:
            return "poor"
        else:
            return "unacceptable"
    
    def _get_completeness_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for completeness issues"""
        recommendations = []
        if any("coverage" in issue.lower() for issue in issues):
            recommendations.append("Review extraction method to capture more source content")
        if any("missing" in issue.lower() for issue in issues):
            recommendations.append("Enhance extraction to capture missing document sections")
        if any("short" in issue.lower() for issue in issues):
            recommendations.append("Verify extraction captured full content, not just summaries")
        return recommendations or ["Review and improve content extraction process"]
    
    def _get_citation_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for citation issues"""
        recommendations = []
        if any("format" in issue.lower() for issue in issues):
            recommendations.append("Standardize legal citation formats")
        if any("reference" in issue.lower() for issue in issues):
            recommendations.append("Verify and repair broken cross-references")
        return recommendations or ["Improve citation extraction and validation"]
    
    def _get_structure_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for structure issues"""
        recommendations = []
        if any("missing" in issue.lower() for issue in issues):
            recommendations.append("Enhance extraction to capture missing structural elements")
        if any("duplicate" in issue.lower() for issue in issues):
            recommendations.append("Review section numbering and remove duplicates")
        if any("short" in issue.lower() for issue in issues):
            recommendations.append("Investigate unusually short sections for extraction errors")
        return recommendations or ["Improve content structure extraction"]
    
    def _get_consistency_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for consistency issues"""
        recommendations = []
        if any("count" in issue.lower() for issue in issues):
            recommendations.append("Investigate extraction method differences")
        if any("similarity" in issue.lower() for issue in issues):
            recommendations.append("Cross-validate content across extraction methods")
        return recommendations or ["Review extraction consistency across methods"]
    
    def _get_coherence_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for coherence issues"""
        recommendations = []
        if any("coherence" in issue.lower() for issue in issues):
            recommendations.append("Review section ordering and logical flow")
        if any("regulatory" in issue.lower() for issue in issues):
            recommendations.append("Verify source contains regulatory content")
        return recommendations or ["Improve semantic analysis of extracted content"]
    
    def _generate_quality_summary(self, score: float, issue_count: int, metadata: Optional[Dict] = None) -> str:
        """Generate human-readable quality summary"""
        if score >= 0.8 and issue_count <= 2:
            return "High quality extraction with minimal issues. Content is ready for use."
        elif score >= 0.6 and issue_count <= 5:
            return "Good quality extraction with some minor issues. Review recommended before use."
        elif score >= 0.4:
            return "Moderate quality extraction with several issues. Manual review required."
        else:
            return "Low quality extraction with significant issues. Re-extraction recommended."