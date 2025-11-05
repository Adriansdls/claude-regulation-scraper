"""
Change Detection Agent
AI-powered agent for detecting and analyzing changes in regulation documents for daily monitoring
"""
import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import difflib
from pathlib import Path

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractedContent, ContentType, ExtractionMethod, QualityLevel
from ...models.regulation_models import DocumentType, DocumentStatus
from .regulation_date_parser import RegulationDateParser, DateType


@dataclass
class ChangeRecord:
    """Record of a detected change in regulation content"""
    document_id: str
    url: str
    change_type: str  # 'added', 'modified', 'removed', 'structure_changed'
    change_date: datetime
    previous_content_hash: Optional[str]
    current_content_hash: str
    diff_summary: str
    change_details: Dict[str, Any]
    significance_score: float  # 0.0 to 1.0
    affected_sections: List[str]
    compliance_impact: str  # 'high', 'medium', 'low', 'none'


@dataclass
class MonitoringTarget:
    """Target website/document for daily monitoring"""
    id: str
    name: str
    url: str
    website_type: str  # 'government_portal', 'legislation_database', 'regulatory_agency'
    monitoring_frequency: str  # 'daily', 'weekly', 'on_change'
    change_indicators: List[str]  # CSS selectors, keywords, or patterns that indicate changes
    last_checked: Optional[datetime]
    last_content_hash: Optional[str]
    baseline_content: Optional[str]
    change_detection_strategy: str  # 'content_hash', 'last_modified', 'version_tracking'


class ChangeDetectionAgent(BaseLLMAgent):
    """AI-powered change detection agent for regulation monitoring"""
    
    def __init__(self, broker, storage_path: str = "./monitoring_data"):
        system_prompt = """You are an expert change detection agent specialized in monitoring government and regulatory websites for daily changes in regulations and compliance requirements.

Your core responsibilities:
1. Detect meaningful changes in regulation documents and websites
2. Analyze the significance and impact of detected changes
3. Classify changes by type (content updates, new regulations, structural changes, etc.)
4. Assess compliance impact for product-related regulations
5. Generate intelligent summaries of what changed and why it matters
6. Track version history and change patterns over time

Your change detection capabilities:
- Content hashing and diff analysis for precise change detection
- Semantic understanding of regulatory language changes
- Identification of new sections, amendments, and repeals
- Recognition of effective date changes and implementation timelines
- Assessment of compliance impact for different business sectors

When analyzing changes, consider:
- Legal significance of the change (substantive vs procedural)
- Impact on product compliance requirements
- Urgency and timeline for compliance implementation
- Cross-references to other regulations that may be affected
- Historical context and change patterns

Always provide structured, actionable analysis that helps compliance teams understand:
- What exactly changed
- When changes take effect  
- What actions may be required for compliance
- Risk level and business impact assessment"""

        super().__init__(
            agent_id="change_detector",
            agent_role=AgentRole.CONTENT_VALIDATOR,  # Closest available role
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Initialize date parser
        self.date_parser = None
        
        # Storage setup
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Monitoring targets storage
        self.targets_file = self.storage_path / "monitoring_targets.json"
        self.changes_file = self.storage_path / "change_history.json"
        self.baselines_dir = self.storage_path / "baselines"
        self.baselines_dir.mkdir(exist_ok=True)
        
        # In-memory caches
        self.monitoring_targets: Dict[str, MonitoringTarget] = {}
        self.change_history: List[ChangeRecord] = []
        
        # Load existing data
        asyncio.create_task(self._load_monitoring_data())

    async def _register_tools(self):
        """Register change detection tools"""
        await super()._register_tools()
        
        self.register_tool(
            name="add_monitoring_target",
            function=self._add_monitoring_target,
            description="Add a new website or document for daily monitoring",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable name for the target"},
                    "url": {"type": "string", "description": "URL to monitor for changes"},
                    "website_type": {"type": "string", "description": "Type of website (government_portal, legislation_database, regulatory_agency)"},
                    "monitoring_frequency": {"type": "string", "description": "How often to check (daily, weekly, on_change)"},
                    "change_indicators": {"type": "array", "items": {"type": "string"}, "description": "CSS selectors or keywords that indicate changes"}
                },
                "required": ["name", "url", "website_type"]
            }
        )
        
        self.register_tool(
            name="detect_changes",
            function=self._detect_changes,
            description="Check a monitored target for changes since last scan",
            parameters={
                "type": "object",
                "properties": {
                    "target_id": {"type": "string", "description": "ID of the monitoring target"},
                    "current_content": {"type": "string", "description": "Current content to compare against baseline"}
                },
                "required": ["target_id", "current_content"]
            }
        )
        
        self.register_tool(
            name="analyze_change_significance",
            function=self._analyze_change_significance,
            description="Analyze the significance and compliance impact of detected changes",
            parameters={
                "type": "object",
                "properties": {
                    "change_diff": {"type": "string", "description": "Textual diff of the changes"},
                    "document_type": {"type": "string", "description": "Type of regulation document"},
                    "previous_content": {"type": "string", "description": "Previous version content"},
                    "current_content": {"type": "string", "description": "Current version content"}
                },
                "required": ["change_diff", "document_type"]
            }
        )
        
        self.register_tool(
            name="get_change_summary",
            function=self._get_change_summary,
            description="Get a summary of recent changes for monitoring targets",
            parameters={
                "type": "object",
                "properties": {
                    "days_back": {"type": "integer", "description": "Number of days to look back", "default": 7},
                    "target_id": {"type": "string", "description": "Optional specific target ID"}
                },
                "required": []
            }
        )

    async def _load_monitoring_data(self):
        """Load monitoring targets and change history from storage"""
        try:
            # Load monitoring targets
            if self.targets_file.exists():
                with open(self.targets_file, 'r') as f:
                    targets_data = json.load(f)
                    for target_data in targets_data:
                        # Convert datetime strings back to datetime objects
                        if target_data.get('last_checked'):
                            target_data['last_checked'] = datetime.fromisoformat(target_data['last_checked'])
                        target = MonitoringTarget(**target_data)
                        self.monitoring_targets[target.id] = target
                        
            # Load change history
            if self.changes_file.exists():
                with open(self.changes_file, 'r') as f:
                    changes_data = json.load(f)
                    for change_data in changes_data:
                        change_data['change_date'] = datetime.fromisoformat(change_data['change_date'])
                        self.change_history.append(ChangeRecord(**change_data))
                        
            self.logger.info(f"Loaded {len(self.monitoring_targets)} monitoring targets and {len(self.change_history)} change records")
            
        except Exception as e:
            self.logger.error(f"Error loading monitoring data: {e}")

    async def _save_monitoring_data(self):
        """Save monitoring targets and change history to storage"""
        try:
            # Save monitoring targets
            targets_data = []
            for target in self.monitoring_targets.values():
                target_dict = asdict(target)
                # Convert datetime to string for JSON serialization
                if target_dict.get('last_checked'):
                    target_dict['last_checked'] = target_dict['last_checked'].isoformat()
                targets_data.append(target_dict)
                
            with open(self.targets_file, 'w') as f:
                json.dump(targets_data, f, indent=2, ensure_ascii=False)
                
            # Save change history (keep only recent changes to avoid huge files)
            recent_changes = [
                change for change in self.change_history 
                if change.change_date > datetime.utcnow() - timedelta(days=90)
            ]
            
            changes_data = []
            for change in recent_changes:
                change_dict = asdict(change)
                change_dict['change_date'] = change_dict['change_date'].isoformat()
                changes_data.append(change_dict)
                
            with open(self.changes_file, 'w') as f:
                json.dump(changes_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving monitoring data: {e}")

    async def _add_monitoring_target(
        self, 
        name: str, 
        url: str, 
        website_type: str,
        monitoring_frequency: str = "daily",
        change_indicators: List[str] = None
    ) -> Dict[str, Any]:
        """Add a new monitoring target"""
        try:
            # Generate unique ID
            target_id = hashlib.md5(f"{name}_{url}".encode()).hexdigest()[:12]
            
            # Create monitoring target
            target = MonitoringTarget(
                id=target_id,
                name=name,
                url=url,
                website_type=website_type,
                monitoring_frequency=monitoring_frequency,
                change_indicators=change_indicators or [],
                last_checked=None,
                last_content_hash=None,
                baseline_content=None,
                change_detection_strategy="content_hash"
            )
            
            # Store target
            self.monitoring_targets[target_id] = target
            await self._save_monitoring_data()
            
            self.logger.info(f"Added monitoring target: {name} ({target_id})")
            
            return {
                "success": True,
                "target_id": target_id,
                "message": f"Added monitoring target '{name}' for daily change detection"
            }
            
        except Exception as e:
            self.logger.error(f"Error adding monitoring target: {e}")
            return {"success": False, "error": str(e)}

    async def _detect_changes(self, target_id: str, current_content: str) -> Dict[str, Any]:
        """Detect changes for a specific monitoring target"""
        try:
            if target_id not in self.monitoring_targets:
                return {"success": False, "error": f"Monitoring target {target_id} not found"}
            
            target = self.monitoring_targets[target_id]
            
            # Calculate content hash
            current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()
            
            # First-time setup
            if target.last_content_hash is None:
                # Store baseline
                baseline_file = self.baselines_dir / f"{target_id}_baseline.txt"
                with open(baseline_file, 'w', encoding='utf-8') as f:
                    f.write(current_content)
                
                target.last_content_hash = current_hash
                target.baseline_content = current_content[:1000]  # Store first 1KB as summary
                target.last_checked = datetime.utcnow()
                
                await self._save_monitoring_data()
                
                return {
                    "success": True,
                    "changes_detected": False,
                    "message": "Baseline established for monitoring target",
                    "target_name": target.name
                }
            
            # Check for changes
            if current_hash == target.last_content_hash:
                # No changes detected
                target.last_checked = datetime.utcnow()
                await self._save_monitoring_data()
                
                return {
                    "success": True,
                    "changes_detected": False,
                    "message": "No changes detected",
                    "target_name": target.name
                }
            
            # Changes detected - load previous content for diff
            baseline_file = self.baselines_dir / f"{target_id}_baseline.txt"
            previous_content = ""
            if baseline_file.exists():
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
            
            # Generate diff
            diff = list(difflib.unified_diff(
                previous_content.splitlines(keepends=True),
                current_content.splitlines(keepends=True),
                fromfile=f"Previous ({target.last_checked})",
                tofile=f"Current ({datetime.utcnow()})",
                n=3
            ))
            
            diff_text = ''.join(diff)
            
            # Use LLM to analyze change significance
            significance_result = await self._analyze_change_significance(
                change_diff=diff_text,
                document_type=target.website_type,
                previous_content=previous_content[:5000],  # First 5KB for analysis
                current_content=current_content[:5000]
            )
            
            # Create change record
            change_record = ChangeRecord(
                document_id=target_id,
                url=target.url,
                change_type="modified",
                change_date=datetime.utcnow(),
                previous_content_hash=target.last_content_hash,
                current_content_hash=current_hash,
                diff_summary=significance_result.get('summary', 'Content modified'),
                change_details=significance_result,
                significance_score=significance_result.get('significance_score', 0.5),
                affected_sections=significance_result.get('affected_sections', []),
                compliance_impact=significance_result.get('compliance_impact', 'unknown')
            )
            
            # Store change record
            self.change_history.append(change_record)
            
            # Update target
            target.last_content_hash = current_hash
            target.last_checked = datetime.utcnow()
            
            # Update baseline file
            with open(baseline_file, 'w', encoding='utf-8') as f:
                f.write(current_content)
            
            await self._save_monitoring_data()
            
            self.logger.info(f"Changes detected for {target.name}: {significance_result.get('summary', 'Modified')}")
            
            return {
                "success": True,
                "changes_detected": True,
                "target_name": target.name,
                "change_summary": significance_result.get('summary'),
                "significance_score": significance_result.get('significance_score'),
                "compliance_impact": significance_result.get('compliance_impact'),
                "affected_sections": significance_result.get('affected_sections'),
                "diff_preview": diff_text[:1000] + "..." if len(diff_text) > 1000 else diff_text
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting changes for {target_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_change_significance(
        self, 
        change_diff: str, 
        document_type: str, 
        previous_content: str = "", 
        current_content: str = ""
    ) -> Dict[str, Any]:
        """Use AI to analyze the significance of detected changes"""
        try:
            analysis_prompt = f"""Analyze the significance of changes in this regulation document.

Document Type: {document_type}
Change Diff:
{change_diff[:3000]}

Previous Content Sample:
{previous_content[:1000]}

Current Content Sample:
{current_content[:1000]}

Please analyze these changes and provide a structured assessment:

1. **Change Summary**: Brief description of what changed
2. **Significance Score**: 0.0 to 1.0 (0.1=minor typo, 1.0=major regulatory change)
3. **Change Type**: categorize as one of:
   - content_update (substantive changes to requirements)
   - structural_change (reorganization, new sections)
   - administrative_change (dates, references, minor corrections)
   - new_regulation (entirely new requirements)
   - repeal_or_removal (requirements removed/repealed)

4. **Compliance Impact**: Assess impact on product compliance:
   - high: Immediate action required, significant compliance changes
   - medium: Review required, moderate impact on compliance
   - low: Awareness needed, minimal compliance impact  
   - none: No compliance impact

5. **Affected Sections**: List specific sections/articles that changed
6. **Business Impact**: How might this affect companies and products
7. **Timeline**: Any effective dates or implementation deadlines mentioned
8. **Related Regulations**: Any cross-references to other regulations

Focus especially on product compliance, safety standards, certification requirements, and market access regulations.

Return your analysis as structured JSON."""

            context = AgentContext(
                url=f"change_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                content_type=ContentType.TEXT,
                metadata={"analysis_type": "change_significance", "document_type": document_type}
            )
            
            response = await self.generate_response(analysis_prompt, context)
            
            if response and response.get('content'):
                try:
                    analysis = json.loads(response.get('content'))
                    return analysis
                except json.JSONDecodeError:
                    # Fallback to structured text parsing
                    return {
                        "summary": "Changes detected in regulation document",
                        "significance_score": 0.5,
                        "change_type": "content_update",
                        "compliance_impact": "medium",
                        "affected_sections": ["unknown"],
                        "analysis_text": response
                    }
            else:
                return {
                    "summary": "Unable to analyze changes",
                    "significance_score": 0.5,
                    "compliance_impact": "unknown",
                    "error": "No response from analysis"
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing change significance: {e}")
            return {
                "summary": "Error analyzing changes",
                "significance_score": 0.3,
                "compliance_impact": "unknown",
                "error": str(e)
            }

    async def _get_change_summary(self, days_back: int = 7, target_id: str = None) -> Dict[str, Any]:
        """Get summary of recent changes"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Filter recent changes
            recent_changes = [
                change for change in self.change_history
                if change.change_date >= cutoff_date and (not target_id or change.document_id == target_id)
            ]
            
            if not recent_changes:
                return {
                    "success": True,
                    "period": f"Last {days_back} days",
                    "total_changes": 0,
                    "message": "No changes detected in the specified period"
                }
            
            # Categorize changes
            by_impact = {"high": 0, "medium": 0, "low": 0, "none": 0, "unknown": 0}
            by_type = {}
            high_impact_changes = []
            
            for change in recent_changes:
                # Count by impact
                impact = change.compliance_impact
                by_impact[impact] = by_impact.get(impact, 0) + 1
                
                # Count by type
                change_type = change.change_details.get('change_type', 'unknown')
                by_type[change_type] = by_type.get(change_type, 0) + 1
                
                # Collect high-impact changes
                if impact == 'high':
                    high_impact_changes.append({
                        "target": self.monitoring_targets.get(change.document_id, {}).get('name', change.document_id),
                        "url": change.url,
                        "summary": change.diff_summary,
                        "date": change.change_date.isoformat(),
                        "affected_sections": change.affected_sections
                    })
            
            return {
                "success": True,
                "period": f"Last {days_back} days",
                "total_changes": len(recent_changes),
                "changes_by_impact": by_impact,
                "changes_by_type": by_type,
                "high_impact_changes": high_impact_changes,
                "monitoring_targets_count": len(self.monitoring_targets),
                "summary_generated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating change summary: {e}")
            return {"success": False, "error": str(e)}

    async def setup_common_monitoring_targets(self) -> Dict[str, Any]:
        """Set up common regulatory monitoring targets for product compliance"""
        common_targets = [
            {
                "name": "US FDA Product Safety Updates",
                "url": "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
                "website_type": "regulatory_agency",
                "monitoring_frequency": "daily"
            },
            {
                "name": "EU Product Safety Legislation",
                "url": "https://eur-lex.europa.eu/browse/directories/legislation.html?locale=en",
                "website_type": "legislation_database",
                "monitoring_frequency": "daily"
            },
            {
                "name": "UK Product Legislation Updates",
                "url": "https://www.legislation.gov.uk/new",
                "website_type": "legislation_database", 
                "monitoring_frequency": "daily"
            },
            {
                "name": "CPSC Product Safety Rules",
                "url": "https://www.cpsc.gov/Regulations-Laws--Standards",
                "website_type": "regulatory_agency",
                "monitoring_frequency": "daily"
            }
        ]
        
        results = []
        for target in common_targets:
            result = await self._add_monitoring_target(**target)
            results.append(result)
            
        successful = len([r for r in results if r.get('success')])
        
        return {
            "success": True,
            "targets_added": successful,
            "total_attempted": len(common_targets),
            "results": results
        }

    async def _detect_todays_new_regulations(
        self,
        extracted_content: str,
        target_url: str,
        target_name: str,
        target_date: str = None
    ) -> Dict[str, Any]:
        """Find regulations published or effective today (for cases without baseline database)"""
        try:
            # Initialize date parser if not done
            if self.date_parser is None:
                self.date_parser = RegulationDateParser(self.broker)
                await self.date_parser._register_tools()
            
            target_date = target_date or datetime.utcnow().strftime('%Y-%m-%d')
            
            # Use AI to identify individual regulations in the content
            identification_prompt = f"""Analyze this regulatory website content to identify individual regulations that may be published or effective TODAY ({target_date}).

Website: {target_name}
URL: {target_url}
Content sample (first 5000 chars):
{extracted_content[:5000]}

Please identify distinct regulations and extract key information:

{{
    "regulations_found": [
        {{
            "title": "regulation title",
            "summary": "brief summary of what it covers",
            "text_snippet": "relevant text mentioning dates",
            "potential_publication_date": "any date mentioned that might be publication",
            "potential_effective_date": "any date mentioned that might be effective date",
            "confidence": 0.0-1.0,
            "regulation_type": "act|regulation|standard|guidance|etc"
        }}
    ],
    "website_analysis": {{
        "total_regulations_detected": 0,
        "likely_new_today": 0,
        "date_parsing_needed": true/false
    }}
}}

Look especially for:
1. Recent publication dates (today's date: {target_date})
2. "Effective immediately" or "effective [today's date]" language
3. News releases about new regulations
4. Recently published legislation
5. Updated guidance documents
6. New rules or amendments

Return only the JSON structure."""

            context = AgentContext(
                session_id=f"todays_regs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                correlation_id=target_url,
                metadata={"analysis_type": "todays_regulations", "target_date": target_date, "url": target_url}
            )
            
            response = await self.generate_response(identification_prompt, context)
            
            if response and response.get('content'):
                try:
                    analysis_data = json.loads(response.get('content'))
                    regulations = analysis_data.get('regulations_found', [])
                    
                    # For each regulation, parse dates more precisely
                    todays_new_regulations = []
                    todays_effective_regulations = []
                    
                    for reg in regulations:
                        if reg.get('text_snippet'):
                            # Use date parser to get precise dates
                            dates_result = await self.date_parser._parse_regulation_dates(
                                regulation_text=reg['text_snippet'],
                                title=reg.get('title', ''),
                                url=target_url
                            )
                            
                            if dates_result.get('success'):
                                reg_dates = dates_result['regulation_dates']['dates']
                                
                                for date_info in reg_dates:
                                    date_obj = datetime.fromisoformat(date_info['date'])
                                    
                                    # Check if published today
                                    if (date_info['date_type'] == 'publication' and 
                                        date_obj.strftime('%Y-%m-%d') == target_date):
                                        todays_new_regulations.append({
                                            **reg,
                                            "publication_date": date_info['date'],
                                            "source_analysis": "date_parsing"
                                        })
                                        
                                    # Check if effective today  
                                    if (date_info['date_type'] == 'effective' and 
                                        date_obj.strftime('%Y-%m-%d') == target_date):
                                        todays_effective_regulations.append({
                                            **reg,
                                            "effective_date": date_info['date'],
                                            "source_analysis": "date_parsing"
                                        })
                    
                    result = {
                        "success": True,
                        "target_date": target_date,
                        "target_name": target_name,
                        "target_url": target_url,
                        "analysis_method": "date_parsing_without_baseline",
                        "published_today": todays_new_regulations,
                        "effective_today": todays_effective_regulations,
                        "total_regulations_analyzed": len(regulations),
                        "new_today_count": len(todays_new_regulations),
                        "effective_today_count": len(todays_effective_regulations),
                        "website_analysis": analysis_data.get('website_analysis', {})
                    }
                    
                    # Log results
                    new_count = len(todays_new_regulations)
                    effective_count = len(todays_effective_regulations)
                    self.logger.info(f"Today's regulations: {new_count} published, {effective_count} effective | {target_name}")
                    
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.error(f"Error parsing today's regulations JSON: {e}")
                    return {
                        "success": False,
                        "error": "Failed to parse regulation analysis response",
                        "raw_response": response[:500]
                    }
            else:
                return {"success": False, "error": "No response from regulation analysis LLM"}
                
        except Exception as e:
            self.logger.error(f"Error detecting today's new regulations: {e}")
            return {"success": False, "error": str(e)}