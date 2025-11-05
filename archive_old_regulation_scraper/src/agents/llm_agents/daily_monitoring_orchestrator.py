"""
Daily Monitoring Orchestrator
Orchestrates daily monitoring of regulatory websites, change detection, and compliance classification
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from .change_detection_agent import ChangeDetectionAgent
from .compliance_classifier_agent import ComplianceClassifierAgent
from .firecrawl_extractor_agent import FirecrawlExtractorAgent
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ContentType


class DailyMonitoringOrchestrator(BaseLLMAgent):
    """Orchestrates the complete daily monitoring workflow"""
    
    def __init__(self, broker, firecrawl_api_key: str = None):
        system_prompt = """You are a daily monitoring orchestrator specialized in coordinating comprehensive regulatory monitoring workflows.

Your responsibilities:
1. **Daily Monitoring Execution**: Run scheduled scans of regulatory websites
2. **Change Detection Coordination**: Identify and analyze changes since last scan
3. **Content Extraction**: Extract full regulation content when changes are detected
4. **Compliance Classification**: Classify changes for product compliance relevance
5. **Alert Generation**: Create prioritized alerts for compliance teams
6. **Workflow Management**: Ensure all monitoring steps complete successfully

Your orchestration capabilities:
- Coordinate multiple specialized agents (extraction, change detection, classification)
- Handle monitoring schedules and retry logic
- Prioritize alerts based on business impact and compliance urgency
- Generate comprehensive daily reports
- Manage monitoring target configuration and optimization

Daily Monitoring Workflow:
1. Load monitoring targets and schedules
2. Check each target for changes using change detection
3. When changes detected, extract full content using Firecrawl
4. Classify extracted content for compliance relevance
5. Generate alerts for high-impact compliance changes
6. Create daily monitoring reports
7. Update monitoring baselines and schedules

Focus on efficiency, reliability, and actionable insights for compliance teams."""

        super().__init__(
            agent_id="daily_monitor_orchestrator",
            agent_role=AgentRole.ORCHESTRATOR,
            broker=broker,
            system_prompt=system_prompt
        )
        
        # Initialize specialized agents
        self.change_detector = ChangeDetectionAgent(broker)
        self.compliance_classifier = ComplianceClassifierAgent(broker)
        self.content_extractor = FirecrawlExtractorAgent(broker, firecrawl_api_key)
        
        # Monitoring configuration
        self.reports_dir = Path("./daily_monitoring_reports")
        self.reports_dir.mkdir(exist_ok=True)

    async def _register_tools(self):
        """Register orchestration tools"""
        await super()._register_tools()
        
        # Register tools from child agents
        await self.change_detector._register_tools()
        await self.compliance_classifier._register_tools()
        await self.content_extractor._register_tools()
        
        self.register_tool(
            name="run_daily_monitoring",
            function=self._run_daily_monitoring,
            description="Execute the complete daily monitoring workflow",
            parameters={
                "type": "object",
                "properties": {
                    "target_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific target IDs to monitor (optional - defaults to all)"
                    },
                    "focus_categories": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Compliance categories to focus on"
                    }
                },
                "required": []
            }
        )
        
        self.register_tool(
            name="setup_monitoring_targets",
            function=self._setup_monitoring_targets,
            description="Set up common product compliance monitoring targets",
            parameters={
                "type": "object",
                "properties": {
                    "target_type": {
                        "type": "string",
                        "description": "Type of targets to set up (product_safety, all, custom)",
                        "default": "product_safety"
                    }
                },
                "required": []
            }
        )
        
        self.register_tool(
            name="generate_monitoring_report",
            function=self._generate_monitoring_report,
            description="Generate comprehensive monitoring report",
            parameters={
                "type": "object",
                "properties": {
                    "report_period_days": {"type": "integer", "default": 1},
                    "include_classifications": {"type": "boolean", "default": True}
                },
                "required": []
            }
        )

    async def _run_daily_monitoring(
        self, 
        target_ids: List[str] = None, 
        focus_categories: List[str] = None
    ) -> Dict[str, Any]:
        """Execute the complete daily monitoring workflow"""
        start_time = datetime.utcnow()
        self.logger.info(f"🚀 Starting daily monitoring workflow at {start_time}")
        
        results = {
            "workflow_start": start_time.isoformat(),
            "targets_monitored": [],
            "changes_detected": [],
            "compliance_relevant_changes": [],
            "high_priority_alerts": [],
            "summary": {},
            "errors": []
        }
        
        try:
            # Step 1: Get monitoring targets
            if not target_ids:
                # Load all targets from change detector
                targets = self.change_detector.monitoring_targets
                target_ids = list(targets.keys())
                self.logger.info(f"📊 Monitoring {len(target_ids)} targets")
            else:
                self.logger.info(f"📊 Monitoring {len(target_ids)} specified targets")
                
            if not target_ids:
                self.logger.warning("⚠️ No monitoring targets configured. Setting up defaults...")
                setup_result = await self._setup_monitoring_targets()
                if setup_result.get('success'):
                    targets = self.change_detector.monitoring_targets
                    target_ids = list(targets.keys())
                
            # Step 2: Check each target for changes
            for target_id in target_ids:
                try:
                    self.logger.info(f"🔍 Checking target: {target_id}")
                    
                    # Get target info
                    target = self.change_detector.monitoring_targets.get(target_id)
                    if not target:
                        self.logger.error(f"Target {target_id} not found")
                        continue
                        
                    results["targets_monitored"].append({
                        "target_id": target_id,
                        "name": target.name,
                        "url": target.url
                    })
                    
                    # Extract current content using Firecrawl
                    self.logger.info(f"📄 Extracting content from: {target.url}")
                    extraction_result = await self.content_extractor._firecrawl_scrape(target.url)
                    
                    if not extraction_result.get('success'):
                        error_msg = f"Content extraction failed for {target.name}: {extraction_result.get('error')}"
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
                        continue
                    
                    current_content = extraction_result.get('markdown', '')
                    if not current_content:
                        error_msg = f"No content extracted for {target.name}"
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
                        continue
                    
                    # Check for changes
                    self.logger.info(f"🔍 Detecting changes for: {target.name}")
                    change_result = await self.change_detector._detect_changes(target_id, current_content)
                    
                    if change_result.get('changes_detected'):
                        change_info = {
                            "target_id": target_id,
                            "target_name": target.name,
                            "url": target.url,
                            "change_summary": change_result.get('change_summary'),
                            "significance_score": change_result.get('significance_score'),
                            "compliance_impact": change_result.get('compliance_impact'),
                            "affected_sections": change_result.get('affected_sections', [])
                        }
                        
                        results["changes_detected"].append(change_info)
                        self.logger.info(f"✅ Changes detected: {target.name} - {change_result.get('change_summary')}")
                        
                        # Step 3: Classify for compliance relevance if changes detected
                        if change_result.get('compliance_impact') in ['high', 'medium']:
                            self.logger.info(f"📋 Classifying compliance relevance: {target.name}")
                            
                            classification_result = await self.compliance_classifier._classify_regulation(
                                regulation_text=current_content,
                                title=target.name,
                                url=target.url,
                                jurisdiction="unknown"  # Could be inferred from URL
                            )
                            
                            if classification_result.get('success') and classification_result.get('is_relevant'):
                                classification = classification_result.get('classification', {})
                                
                                compliance_change = {
                                    **change_info,
                                    "compliance_classification": classification,
                                    "business_implications": classification_result.get('business_implications'),
                                    "key_points": classification_result.get('key_points', [])
                                }
                                
                                results["compliance_relevant_changes"].append(compliance_change)
                                self.logger.info(f"🏷️ Compliance relevant: {target.name} - {classification.get('primary_category')}")
                                
                                # Step 4: Generate high priority alerts
                                if (classification.get('business_impact') in ['critical', 'high'] or 
                                    change_result.get('significance_score', 0) > 0.7):
                                    
                                    alert = {
                                        "alert_level": "HIGH_PRIORITY",
                                        "target_name": target.name,
                                        "url": target.url,
                                        "change_summary": change_result.get('change_summary'),
                                        "business_impact": classification.get('business_impact'),
                                        "compliance_category": classification.get('primary_category'),
                                        "affected_products": classification.get('affected_product_types', []),
                                        "implementation_timeline": classification.get('implementation_timeline'),
                                        "action_required": len(classification.get('compliance_requirements', [])) > 0,
                                        "detected_at": datetime.utcnow().isoformat()
                                    }
                                    
                                    results["high_priority_alerts"].append(alert)
                                    self.logger.warning(f"🚨 HIGH PRIORITY ALERT: {target.name}")
                    
                    else:
                        self.logger.info(f"✅ No changes detected: {target.name}")
                    
                    # Small delay between targets
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error processing target {target_id}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue
            
            # Step 5: Generate summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            results["summary"] = {
                "workflow_completed": end_time.isoformat(),
                "duration_seconds": duration,
                "targets_monitored": len(results["targets_monitored"]),
                "changes_detected": len(results["changes_detected"]),
                "compliance_relevant": len(results["compliance_relevant_changes"]),
                "high_priority_alerts": len(results["high_priority_alerts"]),
                "errors_encountered": len(results["errors"]),
                "success_rate": (len(results["targets_monitored"]) - len(results["errors"])) / max(len(results["targets_monitored"]), 1) * 100
            }
            
            # Save daily report
            report_file = self.reports_dir / f"daily_monitoring_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Daily monitoring completed: {results['summary']['changes_detected']} changes, {results['summary']['high_priority_alerts']} alerts")
            
            return {"success": True, "results": results}
            
        except Exception as e:
            self.logger.error(f"❌ Daily monitoring workflow failed: {e}")
            return {"success": False, "error": str(e), "partial_results": results}

    async def _setup_monitoring_targets(self, target_type: str = "product_safety") -> Dict[str, Any]:
        """Set up monitoring targets for product compliance"""
        if target_type == "product_safety":
            # Product safety focused targets
            targets = [
                {
                    "name": "US CPSC Product Safety Updates",
                    "url": "https://www.cpsc.gov/Newsroom/News-Releases",
                    "website_type": "regulatory_agency",
                    "monitoring_frequency": "daily"
                },
                {
                    "name": "UK Product Safety Legislation",
                    "url": "https://www.legislation.gov.uk/browse/business/consumer-protection",
                    "website_type": "legislation_database",
                    "monitoring_frequency": "daily"
                },
                {
                    "name": "EU Product Safety Regulations", 
                    "url": "https://eur-lex.europa.eu/browse/directories/legislation.html",
                    "website_type": "legislation_database",
                    "monitoring_frequency": "daily"
                },
                {
                    "name": "FDA Product Safety Alerts",
                    "url": "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
                    "website_type": "regulatory_agency",
                    "monitoring_frequency": "daily"
                }
            ]
        else:
            # Comprehensive monitoring targets
            targets = [
                {
                    "name": "US Federal Register - Consumer Products",
                    "url": "https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=consumer+product+safety",
                    "website_type": "government_portal",
                    "monitoring_frequency": "daily"
                },
                {
                    "name": "EU Product Compliance Portal",
                    "url": "https://ec.europa.eu/growth/single-market/goods/new-legislative-framework_en", 
                    "website_type": "regulatory_agency",
                    "monitoring_frequency": "daily"
                }
            ]
        
        # Set up targets using change detection agent
        setup_results = []
        for target in targets:
            result = await self.change_detector._add_monitoring_target(**target)
            setup_results.append(result)
            
        successful = len([r for r in setup_results if r.get('success')])
        
        self.logger.info(f"✅ Set up {successful}/{len(targets)} monitoring targets")
        
        return {
            "success": True,
            "targets_added": successful,
            "total_attempted": len(targets),
            "results": setup_results
        }

    async def _generate_monitoring_report(
        self, 
        report_period_days: int = 1, 
        include_classifications: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        try:
            # Get change summary from change detector
            change_summary = await self.change_detector._get_change_summary(days_back=report_period_days)
            
            # Get classification statistics
            classification_stats = await self.compliance_classifier.get_classification_statistics()
            
            report = {
                "report_generated": datetime.utcnow().isoformat(),
                "report_period_days": report_period_days,
                "monitoring_overview": {
                    "active_targets": len(self.change_detector.monitoring_targets),
                    "total_changes": change_summary.get('total_changes', 0),
                    "changes_by_impact": change_summary.get('changes_by_impact', {}),
                    "high_impact_changes": change_summary.get('high_impact_changes', [])
                }
            }
            
            if include_classifications:
                report["classification_statistics"] = classification_stats
            
            # Save report
            report_file = self.reports_dir / f"monitoring_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
            return {"success": True, "report": report, "report_file": str(report_file)}
            
        except Exception as e:
            self.logger.error(f"Error generating monitoring report: {e}")
            return {"success": False, "error": str(e)}