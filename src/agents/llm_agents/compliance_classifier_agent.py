"""
Product Compliance Classification Agent
AI-powered agent for classifying regulations by product compliance categories and business impact
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractedContent, ContentType
from ...models.regulation_models import DocumentType, Jurisdiction


class ComplianceCategory(str, Enum):
    """Product compliance categories"""
    PRODUCT_SAFETY = "product_safety"
    ELECTRICAL_SAFETY = "electrical_safety" 
    CHEMICAL_SAFETY = "chemical_safety"
    FOOD_SAFETY = "food_safety"
    MEDICAL_DEVICE = "medical_device"
    AUTOMOTIVE = "automotive"
    TOYS_CHILDREN = "toys_children"
    TEXTILES = "textiles"
    COSMETICS = "cosmetics"
    ENVIRONMENTAL = "environmental"
    PACKAGING = "packaging"
    CYBERSECURITY = "cybersecurity"
    DATA_PRIVACY = "data_privacy"
    TELECOM = "telecommunications"
    ENERGY_EFFICIENCY = "energy_efficiency"
    CONSTRUCTION = "construction"
    MACHINERY = "machinery"
    CONSUMER_RIGHTS = "consumer_rights"
    LABELING = "labeling"
    IMPORT_EXPORT = "import_export"
    NOT_PRODUCT_COMPLIANCE = "not_product_compliance"


class BusinessImpact(str, Enum):
    """Business impact levels"""
    CRITICAL = "critical"      # Immediate action required, product recalls possible
    HIGH = "high"             # Major compliance changes, significant business impact
    MEDIUM = "medium"         # Moderate changes, planning required
    LOW = "low"              # Minor changes, awareness needed
    INFORMATIONAL = "informational"  # No direct compliance impact


@dataclass
class ComplianceClassification:
    """Classification result for a regulation"""
    regulation_id: str
    title: str
    url: str
    jurisdiction: str
    
    # Primary classification
    primary_category: ComplianceCategory
    secondary_categories: List[ComplianceCategory]
    confidence_score: float  # 0.0 to 1.0
    
    # Business impact assessment
    business_impact: BusinessImpact
    impact_reasoning: str
    
    # Product scope
    affected_product_types: List[str]
    industry_sectors: List[str]
    
    # Compliance details
    compliance_requirements: List[str]
    implementation_timeline: Optional[str]
    certification_required: bool
    testing_required: bool
    
    # Regulatory context
    related_standards: List[str]
    supersedes_regulations: List[str]
    effective_date: Optional[datetime]
    
    # Classification metadata
    classified_at: datetime
    classifier_confidence: str  # 'high', 'medium', 'low'
    review_required: bool


class ComplianceClassifierAgent(BaseLLMAgent):
    """AI-powered compliance classification agent"""
    
    def __init__(self, broker):
        system_prompt = """You are an expert product compliance classification agent specialized in analyzing regulations to determine their relevance and impact on product compliance across different industries.

Your expertise covers:
- Product Safety & Consumer Protection Laws
- Industry-Specific Regulations (automotive, medical devices, electronics, food, toys, etc.)
- International Standards & Certifications (CE marking, FCC, FDA, CPSC, etc.)
- Environmental & Sustainability Regulations
- Import/Export & Trade Compliance
- Cybersecurity & Data Privacy for Products
- Labeling & Packaging Requirements

Your classification responsibilities:
1. **Relevance Assessment**: Determine if regulation relates to product compliance
2. **Category Classification**: Assign primary and secondary compliance categories
3. **Business Impact Analysis**: Assess urgency and business impact level
4. **Product Scope**: Identify affected product types and industries
5. **Compliance Requirements**: Extract specific compliance actions required
6. **Implementation Timeline**: Identify deadlines and effective dates

Classification Categories to Use:
- product_safety: General product safety requirements
- electrical_safety: Electrical product safety (UL, IEC standards)
- chemical_safety: Chemical substances, RoHS, REACH
- food_safety: Food contact materials, food additives
- medical_device: Medical device regulations, FDA requirements
- automotive: Vehicle safety, automotive standards
- toys_children: Children's product safety, toy regulations
- textiles: Textile safety, flammability standards
- cosmetics: Cosmetic product regulations
- environmental: Environmental impact, sustainability
- packaging: Packaging requirements, waste regulations
- cybersecurity: IoT security, connected device requirements
- data_privacy: Product data collection, privacy requirements
- telecommunications: Telecom equipment, spectrum regulations
- energy_efficiency: Energy labels, efficiency standards
- construction: Building products, construction materials
- machinery: Industrial machinery safety
- consumer_rights: Consumer protection, warranty requirements
- labeling: Product labeling, marking requirements
- import_export: Trade regulations, customs requirements

Business Impact Levels:
- critical: Product recalls, immediate safety issues, severe penalties
- high: Major compliance changes, significant costs, market access risk
- medium: Moderate compliance updates, planning required
- low: Minor changes, limited business impact
- informational: No direct compliance impact, awareness only

Always provide structured, actionable classifications that help compliance teams prioritize their efforts and understand business implications."""

        super().__init__(
            agent_id="compliance_classifier",
            agent_role=AgentRole.CONTENT_VALIDATOR,
            broker=broker,
            system_prompt=system_prompt
        )

    async def _register_tools(self):
        """Register compliance classification tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="classify_regulation",
            function=self._classify_regulation,
            description="Classify a regulation for product compliance relevance and business impact",
            parameters={
                "type": "object",
                "properties": {
                    "regulation_text": {"type": "string", "description": "Full text of the regulation to classify"},
                    "title": {"type": "string", "description": "Title of the regulation"},
                    "url": {"type": "string", "description": "Source URL"},
                    "jurisdiction": {"type": "string", "description": "Legal jurisdiction (US, EU, UK, etc.)"},
                    "document_type": {"type": "string", "description": "Type of document (act, regulation, standard, etc.)"}
                },
                "required": ["regulation_text", "title", "url"]
            }
        )
        
        self.register_tool(
            name="batch_classify_regulations",
            function=self._batch_classify_regulations,
            description="Classify multiple regulations in batch for efficiency",
            parameters={
                "type": "object",
                "properties": {
                    "regulations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"},
                                "url": {"type": "string"},
                                "jurisdiction": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["regulations"]
            }
        )
        
        self.register_tool(
            name="filter_compliance_relevant",
            function=self._filter_compliance_relevant,
            description="Quickly filter regulations to identify those relevant to product compliance",
            parameters={
                "type": "object",
                "properties": {
                    "regulation_summaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "summary": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        }
                    },
                    "focus_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific compliance categories to focus on"
                    }
                },
                "required": ["regulation_summaries"]
            }
        )

    async def _classify_regulation(
        self, 
        regulation_text: str, 
        title: str, 
        url: str,
        jurisdiction: str = "unknown",
        document_type: str = "regulation"
    ) -> Dict[str, Any]:
        """Classify a single regulation for product compliance"""
        try:
            classification_prompt = f"""Analyze this regulation for product compliance relevance and classify it comprehensively.

Regulation Title: {title}
Jurisdiction: {jurisdiction}
Document Type: {document_type}
URL: {url}

Regulation Text:
{regulation_text[:5000]}...

Please provide a comprehensive classification with the following structure:

{{
    "is_product_compliance_relevant": true/false,
    "primary_category": "category_name",
    "secondary_categories": ["category1", "category2"],
    "confidence_score": 0.0-1.0,
    "business_impact": "critical/high/medium/low/informational",
    "impact_reasoning": "Explanation of why this impact level",
    "affected_product_types": ["electronics", "consumer goods", etc.],
    "industry_sectors": ["manufacturing", "retail", etc.],
    "compliance_requirements": ["specific actions required"],
    "implementation_timeline": "deadline or effective date",
    "certification_required": true/false,
    "testing_required": true/false,
    "related_standards": ["ISO 9001", "UL 2089", etc.],
    "supersedes_regulations": ["previous regulation names"],
    "effective_date": "YYYY-MM-DD or null",
    "classifier_confidence": "high/medium/low",
    "review_required": true/false,
    "key_compliance_points": ["bullet point summary of key requirements"],
    "business_implications": "Summary of what businesses need to do"
}}

Focus especially on:
1. Whether this regulation affects physical products, their safety, performance, or market access
2. Specific industries or product categories that must comply
3. Timeline and urgency for compliance implementation
4. Certification, testing, or documentation requirements
5. Penalties or consequences for non-compliance

If the regulation is NOT relevant to product compliance (e.g., purely administrative, tax-related, or service-focused), set is_product_compliance_relevant to false and primary_category to "not_product_compliance".

Return only the JSON structure."""

            context = AgentContext(
                session_id=f"classification_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=url,
                metadata={"classification_type": "product_compliance", "document_type": document_type, "url": url}
            )
            
            response = await self.generate_response(classification_prompt, context)
            
            if response and response.get('content'):
                try:
                    classification_data = json.loads(response.get('content'))
                    
                    # Create classification object
                    classification = ComplianceClassification(
                        regulation_id=url,  # Using URL as ID for now
                        title=title,
                        url=url,
                        jurisdiction=jurisdiction,
                        primary_category=ComplianceCategory(classification_data.get('primary_category', 'not_product_compliance')),
                        secondary_categories=[ComplianceCategory(cat) for cat in classification_data.get('secondary_categories', [])],
                        confidence_score=classification_data.get('confidence_score', 0.5),
                        business_impact=BusinessImpact(classification_data.get('business_impact', 'informational')),
                        impact_reasoning=classification_data.get('impact_reasoning', ''),
                        affected_product_types=classification_data.get('affected_product_types', []),
                        industry_sectors=classification_data.get('industry_sectors', []),
                        compliance_requirements=classification_data.get('compliance_requirements', []),
                        implementation_timeline=classification_data.get('implementation_timeline'),
                        certification_required=classification_data.get('certification_required', False),
                        testing_required=classification_data.get('testing_required', False),
                        related_standards=classification_data.get('related_standards', []),
                        supersedes_regulations=classification_data.get('supersedes_regulations', []),
                        effective_date=datetime.fromisoformat(classification_data['effective_date']) if classification_data.get('effective_date') else None,
                        classified_at=datetime.utcnow(),
                        classifier_confidence=classification_data.get('classifier_confidence', 'medium'),
                        review_required=classification_data.get('review_required', False)
                    )
                    
                    result = {
                        "success": True,
                        "is_relevant": classification_data.get('is_product_compliance_relevant', False),
                        "classification": asdict(classification),
                        "key_points": classification_data.get('key_compliance_points', []),
                        "business_implications": classification_data.get('business_implications', '')
                    }
                    
                    # Log classification result
                    relevance = "RELEVANT" if result['is_relevant'] else "NOT RELEVANT"
                    impact = classification.business_impact.value.upper()
                    category = classification.primary_category.value
                    
                    self.logger.info(f"Classification: {relevance} | {impact} | {category} | {title[:50]}...")
                    
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.error(f"Error parsing classification JSON: {e}")
                    return {
                        "success": False,
                        "error": "Failed to parse classification response",
                        "raw_response": response[:500]
                    }
            else:
                return {"success": False, "error": "No response from classification LLM"}
                
        except Exception as e:
            self.logger.error(f"Error classifying regulation: {e}")
            return {"success": False, "error": str(e)}

    async def _batch_classify_regulations(self, regulations: List[Dict[str, str]]) -> Dict[str, Any]:
        """Classify multiple regulations in batch"""
        try:
            results = []
            relevant_count = 0
            
            for regulation in regulations:
                result = await self._classify_regulation(
                    regulation_text=regulation.get('text', ''),
                    title=regulation.get('title', ''),
                    url=regulation.get('url', ''),
                    jurisdiction=regulation.get('jurisdiction', 'unknown')
                )
                
                if result.get('success') and result.get('is_relevant'):
                    relevant_count += 1
                    
                results.append({
                    "regulation_id": regulation.get('id'),
                    "classification_result": result
                })
                
                # Small delay to avoid overwhelming the LLM API
                await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "total_classified": len(regulations),
                "relevant_regulations": relevant_count,
                "relevance_rate": relevant_count / len(regulations) * 100 if regulations else 0,
                "classifications": results
            }
            
        except Exception as e:
            self.logger.error(f"Error in batch classification: {e}")
            return {"success": False, "error": str(e)}

    async def _filter_compliance_relevant(
        self, 
        regulation_summaries: List[Dict[str, str]], 
        focus_categories: List[str] = None
    ) -> Dict[str, Any]:
        """Quickly filter regulations for compliance relevance"""
        try:
            # Create a focused filtering prompt
            summaries_text = "\n".join([
                f"ID: {reg['id']} | Title: {reg['title']} | Summary: {reg.get('summary', 'No summary')}"
                for reg in regulation_summaries[:50]  # Limit to avoid token limits
            ])
            
            focus_filter = ""
            if focus_categories:
                focus_filter = f"\nFocus especially on these categories: {', '.join(focus_categories)}"
            
            filter_prompt = f"""Review these regulation summaries and identify which ones are likely relevant to PRODUCT COMPLIANCE.

Product compliance includes: product safety, certification requirements, testing standards, labeling rules, import/export requirements for physical goods, industry-specific product regulations, etc.

NOT product compliance: pure administrative rules, tax regulations, service regulations, employment law, general business regulations, etc.

Regulations to Review:
{summaries_text}
{focus_filter}

For each regulation, respond with ONLY the regulation ID if it appears relevant to product compliance. List only the IDs, one per line, no explanations.

Example format:
REG001
REG005
REG012

Only list IDs that are LIKELY relevant to product compliance requirements."""

            context = AgentContext(
                session_id=f"filter_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id="batch_filter",
                metadata={"filter_type": "compliance_relevance", "count": len(regulation_summaries)}
            )
            
            response = await self.generate_response(filter_prompt, context)
            
            if response:
                # Parse the response to extract relevant IDs
                relevant_ids = [
                    line.strip() for line in response.strip().split('\n') 
                    if line.strip() and not line.strip().startswith('#')
                ]
                
                # Match against provided regulations
                relevant_regulations = [
                    reg for reg in regulation_summaries 
                    if reg['id'] in relevant_ids
                ]
                
                return {
                    "success": True,
                    "total_reviewed": len(regulation_summaries),
                    "potentially_relevant": len(relevant_regulations),
                    "relevance_rate": len(relevant_regulations) / len(regulation_summaries) * 100 if regulation_summaries else 0,
                    "relevant_regulation_ids": relevant_ids,
                    "relevant_regulations": relevant_regulations
                }
            else:
                return {"success": False, "error": "No response from filtering LLM"}
                
        except Exception as e:
            self.logger.error(f"Error filtering regulations: {e}")
            return {"success": False, "error": str(e)}

    async def get_classification_statistics(self) -> Dict[str, Any]:
        """Get statistics about classification patterns"""
        # This would typically query a database, but for now return structure
        return {
            "total_classified": 0,
            "by_category": {category.value: 0 for category in ComplianceCategory},
            "by_impact": {impact.value: 0 for impact in BusinessImpact},
            "by_jurisdiction": {},
            "high_impact_recent": [],
            "classification_accuracy": 0.85  # Would be calculated from validation data
        }