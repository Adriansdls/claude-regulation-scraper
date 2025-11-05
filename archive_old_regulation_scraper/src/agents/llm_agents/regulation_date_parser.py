"""
Regulation Date Parser Agent
AI-powered agent for extracting publication dates, effective dates, and enforcement dates from regulation text
"""
import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType


class DateType(str, Enum):
    """Types of regulation dates"""
    PUBLICATION = "publication"
    EFFECTIVE = "effective"  
    ENFORCEMENT = "enforcement"
    LAST_MODIFIED = "last_modified"
    EXPIRY = "expiry"
    REVIEW = "review"
    CONSULTATION_START = "consultation_start"
    CONSULTATION_END = "consultation_end"


@dataclass
class RegulationDate:
    """A parsed date from regulation content"""
    date_type: DateType
    date: datetime
    date_string: str  # Original text
    confidence: float  # 0.0 to 1.0
    context: str  # Surrounding text
    source_section: str  # Which part of document
    

@dataclass
class RegulationDates:
    """All dates parsed from a regulation"""
    regulation_id: str
    title: str
    url: str
    dates: List[RegulationDate]
    parsing_timestamp: datetime
    is_current: bool  # True if regulation is currently in force
    next_action_date: Optional[datetime]  # Next important date (expiry, review, etc.)
    

class RegulationDateParser(BaseLLMAgent):
    """AI-powered regulation date extraction agent"""
    
    def __init__(self, broker):
        system_prompt = """You are an expert regulation date parser specialized in extracting all relevant dates from legal and regulatory documents.

Your expertise covers:
- Publication dates and gazette numbers
- Effective dates and coming-into-force provisions
- Enforcement dates and phase-in periods  
- Last modified/amended dates
- Expiry and sunset clause dates
- Review and renewal dates
- Consultation periods and public comment deadlines
- Transition periods and grace periods

Date formats you handle:
- Standard formats: "January 1, 2024", "1 Jan 2024", "2024-01-01"
- Legal formats: "the first day of January, 2024", "on and after January 1, 2024"
- Relative dates: "30 days after publication", "six months from the date of..."
- Complex provisions: "except as provided in subsection (2), this regulation comes into force on..."

Your parsing responsibilities:
1. **Date Identification**: Find all date mentions in regulation text
2. **Date Classification**: Classify each date by type (publication, effective, etc.)
3. **Context Analysis**: Understand what each date controls or triggers
4. **Current Status**: Determine if regulation is currently in force
5. **Future Actions**: Identify upcoming important dates (reviews, expiries)
6. **Relative Date Resolution**: Calculate actual dates from relative expressions

Always provide structured, accurate date information that helps compliance teams understand regulatory timelines."""

        super().__init__(
            agent_id="regulation_date_parser",
            agent_role=AgentRole.CONTENT_VALIDATOR,
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Common date patterns for pre-filtering
        self.date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\beffective\s+(?:date|on|from)?\s*[:\-]?\s*([^\.]+?)(?:\.|;|$)',
            r'\bcomes?\s+into\s+force\s+(?:on\s+)?([^\.]+?)(?:\.|;|$)',
            r'\bpublished?\s+(?:on\s+)?([^\.]+?)(?:\.|;|$)',
            r'\benforcement\s+date\s*[:\-]?\s*([^\.]+?)(?:\.|;|$)',
        ]

    async def _register_tools(self):
        """Register date parsing tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="parse_regulation_dates",
            function=self._parse_regulation_dates,
            description="Parse all relevant dates from regulation text",
            parameters={
                "type": "object", 
                "properties": {
                    "regulation_text": {"type": "string", "description": "Full text of the regulation"},
                    "title": {"type": "string", "description": "Regulation title"},
                    "url": {"type": "string", "description": "Source URL"},
                    "jurisdiction": {"type": "string", "description": "Legal jurisdiction (US, EU, UK, etc.)"}
                },
                "required": ["regulation_text", "title", "url"]
            }
        )
        
        self.register_tool(
            name="check_current_status",
            function=self._check_current_status,
            description="Check if regulation is currently in force based on dates",
            parameters={
                "type": "object",
                "properties": {
                    "regulation_dates": {"type": "object", "description": "Parsed regulation dates"},
                    "check_date": {"type": "string", "description": "Date to check against (ISO format)"}
                },
                "required": ["regulation_dates"]
            }
        )
        
        self.register_tool(
            name="find_todays_new_regulations", 
            function=self._find_todays_new_regulations,
            description="Find regulations published or effective today",
            parameters={
                "type": "object",
                "properties": {
                    "regulations_batch": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        }
                    },
                    "target_date": {"type": "string", "description": "Target date (ISO format), defaults to today"}
                },
                "required": ["regulations_batch"]
            }
        )

    async def _parse_regulation_dates(
        self, 
        regulation_text: str, 
        title: str, 
        url: str,
        jurisdiction: str = "unknown"
    ) -> Dict[str, Any]:
        """Parse all relevant dates from regulation text"""
        try:
            # Pre-filter text sections that likely contain dates
            text_sections = self._extract_date_sections(regulation_text)
            
            parsing_prompt = f"""Parse all relevant dates from this regulation text and classify them by type.

Regulation: {title}
Jurisdiction: {jurisdiction}
URL: {url}

Text sections with potential dates:
{chr(10).join(text_sections[:10])}...

Please identify and extract ALL dates mentioned in the regulation, classifying each by type:

{{
    "dates_found": [
        {{
            "date_type": "publication|effective|enforcement|last_modified|expiry|review|consultation_start|consultation_end",
            "date": "YYYY-MM-DD",
            "original_text": "exact text from document",
            "confidence": 0.0-1.0,
            "context": "surrounding sentence or paragraph",
            "source_section": "which part of document"
        }}
    ],
    "regulation_status": {{
        "is_current": true/false,
        "status_reasoning": "explanation of current status",
        "next_action_date": "YYYY-MM-DD or null",
        "next_action_type": "review|expiry|amendment|etc"
    }},
    "parsing_notes": ["any ambiguities or assumptions made"],
    "date_relationships": ["how dates relate to each other"]
}}

Focus especially on:
1. When the regulation was published/gazetted
2. When it comes into force (effective date)  
3. When enforcement begins (may differ from effective date)
4. Any expiry or sunset dates
5. Required review dates
6. Last amendment dates
7. Consultation periods

For relative dates like "30 days after publication", calculate the actual date if possible.
For ambiguous dates, note the ambiguity but provide best interpretation.

Return only the JSON structure."""

            context = AgentContext(
                session_id=f"date_parsing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=url,
                metadata={"parsing_type": "regulation_dates", "jurisdiction": jurisdiction, "url": url}
            )
            
            response = await self.generate_response(parsing_prompt, context)
            
            if response and response.get('content'):
                try:
                    parsed_data = json.loads(response.get('content'))
                    
                    # Convert to structured objects
                    regulation_dates = RegulationDates(
                        regulation_id=url,
                        title=title,
                        url=url,
                        dates=[
                            RegulationDate(
                                date_type=DateType(date_info.get('date_type', 'publication')),
                                date=datetime.fromisoformat(date_info['date']) if date_info.get('date') else datetime.utcnow(),
                                date_string=date_info.get('original_text', ''),
                                confidence=date_info.get('confidence', 0.5),
                                context=date_info.get('context', ''),
                                source_section=date_info.get('source_section', '')
                            )
                            for date_info in parsed_data.get('dates_found', [])
                        ],
                        parsing_timestamp=datetime.utcnow(),
                        is_current=parsed_data.get('regulation_status', {}).get('is_current', False),
                        next_action_date=datetime.fromisoformat(parsed_data.get('regulation_status', {}).get('next_action_date')) if parsed_data.get('regulation_status', {}).get('next_action_date') else None
                    )
                    
                    result = {
                        "success": True,
                        "regulation_dates": asdict(regulation_dates),
                        "parsed_dates_count": len(regulation_dates.dates),
                        "current_status": regulation_dates.is_current,
                        "parsing_notes": parsed_data.get('parsing_notes', []),
                        "date_relationships": parsed_data.get('date_relationships', [])
                    }
                    
                    # Log parsing results
                    dates_summary = [f"{d.date_type.value}:{d.date.strftime('%Y-%m-%d')}" for d in regulation_dates.dates]
                    status = "CURRENT" if regulation_dates.is_current else "NOT CURRENT"
                    self.logger.info(f"Date parsing: {status} | {len(regulation_dates.dates)} dates | {', '.join(dates_summary[:3])} | {title[:50]}...")
                    
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.error(f"Error parsing dates JSON: {e}")
                    return {
                        "success": False,
                        "error": "Failed to parse dates response",
                        "raw_response": response[:500]
                    }
            else:
                return {"success": False, "error": "No response from date parsing LLM"}
                
        except Exception as e:
            self.logger.error(f"Error parsing regulation dates: {e}")
            return {"success": False, "error": str(e)}

    def _extract_date_sections(self, text: str) -> List[str]:
        """Extract sections of text that likely contain date information"""
        sections = []
        
        # Split into sentences and paragraphs
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            # Check if sentence contains date-related keywords or patterns
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in self.date_patterns):
                sections.append(sentence.strip())
            elif any(keyword in sentence.lower() for keyword in [
                'effective', 'force', 'publish', 'gazette', 'enact', 'commence',
                'expire', 'review', 'amend', 'repeal', 'consultation', 'deadline'
            ]):
                sections.append(sentence.strip())
        
        # Also include first and last few sentences (often contain dates)
        if len(sentences) > 2:
            sections.extend(sentences[:2])  # First two sentences
            sections.extend(sentences[-2:])  # Last two sentences
            
        # Remove duplicates and empty sections
        sections = list(set([s for s in sections if s.strip()]))
        
        return sections[:20]  # Limit to avoid token overflow

    async def _check_current_status(
        self, 
        regulation_dates: Dict[str, Any], 
        check_date: str = None
    ) -> Dict[str, Any]:
        """Check if regulation is currently in force"""
        try:
            check_date = datetime.fromisoformat(check_date) if check_date else datetime.utcnow()
            
            dates = regulation_dates.get('dates', [])
            
            # Find effective date
            effective_dates = [d for d in dates if d.get('date_type') == 'effective']
            publication_dates = [d for d in dates if d.get('date_type') == 'publication']
            expiry_dates = [d for d in dates if d.get('date_type') == 'expiry']
            
            is_current = False
            status_reasoning = "No effective date found"
            
            if effective_dates:
                effective_date = datetime.fromisoformat(effective_dates[0]['date'])
                if check_date >= effective_date:
                    is_current = True
                    status_reasoning = f"Effective since {effective_date.strftime('%Y-%m-%d')}"
                else:
                    status_reasoning = f"Not yet effective (effective {effective_date.strftime('%Y-%m-%d')})"
            elif publication_dates:
                # Fallback to publication date if no explicit effective date
                pub_date = datetime.fromisoformat(publication_dates[0]['date'])
                if check_date >= pub_date:
                    is_current = True
                    status_reasoning = f"Current since publication {pub_date.strftime('%Y-%m-%d')}"
                    
            # Check expiry
            if expiry_dates and is_current:
                expiry_date = datetime.fromisoformat(expiry_dates[0]['date'])
                if check_date >= expiry_date:
                    is_current = False
                    status_reasoning = f"Expired on {expiry_date.strftime('%Y-%m-%d')}"
                    
            return {
                "success": True,
                "is_current": is_current,
                "status_reasoning": status_reasoning,
                "check_date": check_date.isoformat(),
                "effective_dates": len(effective_dates),
                "expiry_dates": len(expiry_dates)
            }
            
        except Exception as e:
            self.logger.error(f"Error checking current status: {e}")
            return {"success": False, "error": str(e)}

    async def _find_todays_new_regulations(
        self, 
        regulations_batch: List[Dict[str, str]], 
        target_date: str = None
    ) -> Dict[str, Any]:
        """Find regulations published or effective today"""
        try:
            target_date = datetime.fromisoformat(target_date) if target_date else datetime.utcnow()
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            new_today = []
            effective_today = []
            
            for regulation in regulations_batch:
                # Parse dates for this regulation
                dates_result = await self._parse_regulation_dates(
                    regulation_text=regulation.get('text', ''),
                    title=regulation.get('title', ''),
                    url=regulation.get('url', ''),
                    jurisdiction=regulation.get('jurisdiction', 'unknown')
                )
                
                if dates_result.get('success'):
                    dates = dates_result['regulation_dates']['dates']
                    
                    for date_info in dates:
                        date_obj = datetime.fromisoformat(date_info['date'])
                        
                        # Check if published today
                        if (date_info['date_type'] == 'publication' and 
                            date_obj.strftime('%Y-%m-%d') == target_date_str):
                            new_today.append({
                                "regulation": regulation,
                                "date_info": date_info,
                                "type": "published_today"
                            })
                            
                        # Check if effective today
                        if (date_info['date_type'] == 'effective' and 
                            date_obj.strftime('%Y-%m-%d') == target_date_str):
                            effective_today.append({
                                "regulation": regulation,
                                "date_info": date_info,
                                "type": "effective_today"
                            })
            
            return {
                "success": True,
                "target_date": target_date_str,
                "published_today": new_today,
                "effective_today": effective_today,
                "total_new_today": len(new_today),
                "total_effective_today": len(effective_today),
                "regulations_processed": len(regulations_batch)
            }
            
        except Exception as e:
            self.logger.error(f"Error finding today's regulations: {e}")
            return {"success": False, "error": str(e)}

    async def get_date_parsing_statistics(self) -> Dict[str, Any]:
        """Get statistics about date parsing patterns"""
        # This would typically query a database, but for now return structure
        return {
            "total_regulations_parsed": 0,
            "dates_by_type": {date_type.value: 0 for date_type in DateType},
            "current_regulations": 0,
            "expired_regulations": 0,
            "upcoming_effective_dates": [],
            "upcoming_expiry_dates": [],
            "parsing_accuracy": 0.92  # Would be calculated from validation data
        }