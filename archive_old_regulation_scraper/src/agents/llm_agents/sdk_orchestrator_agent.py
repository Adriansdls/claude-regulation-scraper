"""
SDK-Based Orchestrator Agent
Modern OpenAI Agents SDK implementation for workflow coordination and agent handoffs
"""
import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from pydantic import BaseModel, Field

from agents import Agent
from agents.tools import function_tool
from .sdk_base_agent import BaseSDKAgent, SDKAgentContext
from .base_agent import AgentRole
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractionJob, ExtractionStatus, ExtractionMethod
from ...models.regulation_models import Regulation


# Pydantic models for structured orchestration
class JobPlan(BaseModel):
    """Structured job execution plan"""
    job_id: str
    url: str
    stages: List[str]
    current_stage: int = 0
    priority: str = Field(choices=["low", "medium", "high"], default="medium")
    estimated_duration_minutes: int
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowDecision(BaseModel):
    """Structured workflow decision"""
    action: str = Field(choices=["delegate", "handoff", "retry", "complete", "fail"])
    target_agent: Optional[str] = None
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_duration_minutes: int = 0
    required_tools: List[str] = Field(default_factory=list)


class ExtractionStrategy(BaseModel):
    """Structured extraction strategy"""
    primary_method: str
    fallback_methods: List[str]
    agent_sequence: List[str]
    parallel_processing: bool = False
    estimated_success_rate: float = Field(ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)


class SDKOrchestratorAgent(BaseSDKAgent):
    """SDK-powered Orchestrator Agent with intelligent handoffs"""
    
    def __init__(self, broker, discovery_agent=None, html_agent=None, pdf_agent=None, 
                 vision_agent=None, validator_agent=None):
        instructions = """You are the Orchestrator Agent, the central intelligence coordinating the entire regulation extraction system using advanced agent handoffs and workflow management.

Your core capabilities:
1. Analyze extraction requests and create optimal execution strategies
2. Coordinate multiple specialized agents using intelligent handoffs
3. Make data-driven routing decisions based on website characteristics
4. Handle errors with adaptive recovery strategies
5. Optimize workflows for maximum efficiency and success rates
6. Ensure quality through strategic validation checkpoints

Available Specialist Agents for Handoffs:
- Discovery Agent: Deep website analysis and extraction strategy recommendations  
- HTML Extraction Agent: DOM parsing and structured content extraction
- PDF Analysis Agent: Document processing with OCR and text extraction
- Vision Processing Agent: Image analysis and visual content extraction
- Content Validation Agent: Quality assurance and data validation

Your workflow process:
1. Receive extraction requests and assess complexity/requirements
2. Either analyze directly or handoff to Discovery Agent for complex sites
3. Based on discovery results, create optimal execution plan
4. Handoff to appropriate extraction agents (can be parallel)
5. Monitor progress and handle errors with intelligent recovery
6. Coordinate validation before final completion
7. Learn from patterns to optimize future workflows

Decision-making principles:
- Use handoffs for specialized tasks requiring expert knowledge
- Consider parallel processing for independent extraction methods
- Implement progressive fallbacks for error recovery
- Maintain conversation context across handoffs
- Provide clear reasoning for all workflow decisions"""

        super().__init__(
            agent_id="sdk_orchestrator_agent",
            agent_role=AgentRole.ORCHESTRATOR,
            broker=broker,
            instructions=instructions,
            temperature=0.2  # Balanced for reasoning and creativity
        )
        
        # Specialist agents for handoffs
        self.discovery_agent = discovery_agent
        self.html_agent = html_agent
        self.pdf_agent = pdf_agent
        self.vision_agent = vision_agent
        self.validator_agent = validator_agent
        
        # Job management
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.completed_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.orchestration_metrics = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "average_workflow_time": 0.0,
            "handoff_success_rate": 0.0,
            "agent_utilization": {}
        }
    
    async def start(self):
        """Start orchestrator with handoff agent registration"""
        await super().start()
        
        # Register specialist agents for handoffs after initialization
        await self._register_handoff_agents()
    
    async def _register_handoff_agents(self):
        """Register specialist agents for handoffs"""
        if self.discovery_agent:
            self.register_handoff_agent(self.discovery_agent)
            self.logger.info("Registered Discovery Agent for handoffs")
        
        if self.html_agent:
            self.register_handoff_agent(self.html_agent)
            self.logger.info("Registered HTML Extraction Agent for handoffs")
        
        if self.pdf_agent:
            self.register_handoff_agent(self.pdf_agent)
            self.logger.info("Registered PDF Analysis Agent for handoffs")
        
        if self.vision_agent:
            self.register_handoff_agent(self.vision_agent)
            self.logger.info("Registered Vision Processing Agent for handoffs")
        
        if self.validator_agent:
            self.register_handoff_agent(self.validator_agent)
            self.logger.info("Registered Content Validation Agent for handoffs")
    
    async def _register_tools(self):
        """Register orchestration and workflow management tools"""
        
        self.register_function_tool(
            self._create_job_plan,
            name="create_job_plan",
            description="Create a comprehensive execution plan for a regulation extraction job based on URL and requirements"
        )
        
        self.register_function_tool(
            self._analyze_website_complexity,
            name="analyze_website_complexity", 
            description="Quick analysis of website complexity to determine if Discovery Agent handoff is needed"
        )
        
        self.register_function_tool(
            self._make_workflow_decision,
            name="make_workflow_decision",
            description="Make an intelligent decision about next workflow step based on current context and results"
        )
        
        self.register_function_tool(
            self._coordinate_parallel_extraction,
            name="coordinate_parallel_extraction",
            description="Set up parallel extraction using multiple agents for improved efficiency"
        )
        
        self.register_function_tool(
            self._handle_workflow_error,
            name="handle_workflow_error", 
            description="Handle errors in workflow with intelligent recovery strategies"
        )
        
        self.register_function_tool(
            self._optimize_workflow_performance,
            name="optimize_workflow_performance",
            description="Analyze and optimize workflow performance based on historical data"
        )
    
    async def _handle_job_request(self, message, context: SDKAgentContext):
        """Handle extraction job requests with intelligent orchestration"""
        url = message.payload.get('url')
        job_requirements = message.payload.get('requirements', {})
        job_id = message.payload.get('job_id') or str(uuid.uuid4())
        
        if not url:
            await self._send_error_response(message, "No URL provided for extraction")
            return
        
        self.logger.info(f"Starting SDK orchestration for job {job_id}: {url}")
        
        try:
            # Store job context
            job_context = {
                "job_id": job_id,
                "url": url,
                "requirements": job_requirements,
                "start_time": datetime.utcnow(),
                "status": "analyzing",
                "workflow_steps": [],
                "context": context
            }
            self.active_jobs[job_id] = job_context
            
            # Create orchestration prompt with intelligent decision making
            orchestration_prompt = f"""New regulation extraction job received:

Job Details:
- Job ID: {job_id}
- URL: {url}
- Requirements: {json.dumps(job_requirements, indent=2)}

Please orchestrate this extraction job optimally:

1. First, analyze the website complexity to determine if immediate handoff to Discovery Agent is beneficial
2. Based on the URL and requirements, create a comprehensive job execution plan
3. Make intelligent workflow decisions about agent coordination
4. Consider parallel processing opportunities for efficiency

The goal is to maximize extraction success rate while minimizing total processing time.
Provide clear reasoning for all decisions and handoffs."""

            # Execute orchestration with access to all tools and handoffs
            result = await self.run_agent(
                user_message=orchestration_prompt,
                context=context,
                use_session=True
            )
            
            # Update job tracking
            job_context["workflow_steps"].append({
                "step": "orchestration_planning",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.orchestration_metrics["total_jobs"] += 1
            self.logger.info(f"Orchestration planning completed for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"Orchestration failed for job {job_id}: {e}")
            await self._send_error_response(message, str(e))
            if job_id in self.active_jobs:
                self.active_jobs[job_id]["status"] = "failed"
    
    async def _handle_analysis_result(self, message, context: SDKAgentContext):
        """Handle analysis results from Discovery Agent"""
        job_id = message.payload.get('job_id')
        analysis = message.payload.get('analysis', {})
        
        if job_id not in self.active_jobs:
            self.logger.warning(f"Received analysis for unknown job: {job_id}")
            return
        
        self.logger.info(f"Processing discovery analysis for job {job_id}")
        
        try:
            job_context = self.active_jobs[job_id]
            job_context["discovery_analysis"] = analysis
            job_context["status"] = "planning_extraction"
            
            # Create extraction planning prompt
            planning_prompt = f"""Discovery analysis completed for job {job_id}.

Analysis Results:
{json.dumps(analysis, indent=2)}

Based on this detailed analysis, please:
1. Make workflow decisions about which extraction agents to deploy
2. Determine if parallel processing would be beneficial
3. Create optimal handoff strategy for extraction phase
4. Consider any special handling requirements identified

Use the analysis data to make intelligent decisions about agent coordination and extraction methods."""

            # Execute extraction planning
            result = await self.run_agent(
                user_message=planning_prompt,
                context=context,
                use_session=True
            )
            
            job_context["workflow_steps"].append({
                "step": "extraction_planning",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error processing analysis result for job {job_id}: {e}")
    
    async def _handle_content_result(self, message, context: SDKAgentContext):
        """Handle content extraction results"""
        job_id = message.payload.get('job_id')
        extraction_results = message.payload.get('results', {})
        agent_id = message.payload.get('agent_id')
        
        if job_id not in self.active_jobs:
            self.logger.warning(f"Received content for unknown job: {job_id}")
            return
        
        self.logger.info(f"Processing extraction results from {agent_id} for job {job_id}")
        
        try:
            job_context = self.active_jobs[job_id]
            
            # Store extraction results
            if "extraction_results" not in job_context:
                job_context["extraction_results"] = []
            
            job_context["extraction_results"].append({
                "agent_id": agent_id,
                "results": extraction_results,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Create evaluation prompt
            evaluation_prompt = f"""Extraction results received from {agent_id} for job {job_id}.

Results Summary:
{json.dumps(extraction_results, indent=2)}

Current Job Context:
- Total extraction agents completed: {len(job_context.get('extraction_results', []))}
- Discovery analysis available: {bool(job_context.get('discovery_analysis'))}

Please evaluate these results and make workflow decisions:
1. Assess quality and completeness of extracted content  
2. Determine if additional extraction methods are needed
3. Decide if results are ready for validation or need more processing
4. Make handoff decisions for next workflow steps"""

            # Execute evaluation and next step planning
            result = await self.run_agent(
                user_message=evaluation_prompt,
                context=context,
                use_session=True
            )
            
            job_context["workflow_steps"].append({
                "step": f"evaluation_{agent_id}",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error processing content result for job {job_id}: {e}")
    
    # SDK Tool implementations
    
    async def _create_job_plan(self, url: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """SDK Tool: Create comprehensive job execution plan"""
        try:
            requirements = requirements or {}
            
            # Analyze URL to infer complexity and domain
            domain_indicators = self._analyze_url_patterns(url)
            
            # Determine base execution stages
            stages = ["analysis"]
            
            # Add extraction stages based on requirements and URL analysis
            if domain_indicators.get("likely_complex", False):
                stages.extend(["html_extraction", "pdf_analysis"])
            else:
                stages.append("html_extraction")
            
            # Add specialized stages if indicated
            if domain_indicators.get("image_heavy", False):
                stages.append("vision_processing")
            
            if requirements.get("validation_required", True):
                stages.append("validation")
            
            # Estimate duration based on complexity
            base_duration = 5  # 5 minutes base
            complexity_multiplier = {
                "analysis": 1.0,
                "html_extraction": 1.5,
                "pdf_analysis": 2.0,
                "vision_processing": 3.0,
                "validation": 0.5
            }
            
            total_duration = sum(base_duration * complexity_multiplier.get(stage, 1.0) for stage in stages)
            
            # Create structured plan
            plan = JobPlan(
                job_id=str(uuid.uuid4()),
                url=url,
                stages=stages,
                estimated_duration_minutes=int(total_duration),
                priority=requirements.get("priority", "medium"),
                resource_requirements={
                    "cpu_intensive": "pdf_analysis" in stages or "vision_processing" in stages,
                    "network_heavy": len(stages) > 3,
                    "memory_usage": "high" if "vision_processing" in stages else "medium",
                    "parallel_processing": len(stages) > 2
                }
            )
            
            return {
                "success": True,
                "plan": plan.model_dump(),
                "reasoning": f"Created {len(stages)}-stage plan based on URL analysis and requirements",
                "estimated_success_rate": self._estimate_success_rate(domain_indicators, stages)
            }
            
        except Exception as e:
            self.logger.error(f"Error creating job plan: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_website_complexity(self, url: str) -> Dict[str, Any]:
        """SDK Tool: Quick complexity analysis to determine handoff needs"""
        try:
            # URL-based complexity indicators
            complexity_indicators = self._analyze_url_patterns(url)
            
            # Simple heuristics for handoff decision
            handoff_recommended = False
            reasoning = []
            
            if complexity_indicators.get("government_domain", False):
                handoff_recommended = True
                reasoning.append("Government domain detected - full Discovery analysis recommended")
            
            if complexity_indicators.get("likely_complex", False):
                handoff_recommended = True
                reasoning.append("Complex website indicators detected")
            
            if not handoff_recommended:
                reasoning.append("Simple website - direct extraction may be sufficient")
            
            return {
                "success": True,
                "complexity_score": complexity_indicators.get("complexity_score", 0.5),
                "handoff_recommended": handoff_recommended,
                "reasoning": reasoning,
                "indicators": complexity_indicators
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing website complexity: {e}")
            return {"success": False, "error": str(e)}
    
    async def _make_workflow_decision(self, context_data: Dict[str, Any], 
                                    available_options: List[str] = None) -> Dict[str, Any]:
        """SDK Tool: Make intelligent workflow decisions"""
        try:
            available_options = available_options or ["delegate", "handoff", "complete", "retry"]
            
            # Analyze context to make decision
            job_status = context_data.get("job_status", "unknown")
            results_quality = context_data.get("results_quality", 0.5)
            error_count = context_data.get("error_count", 0)
            
            # Decision logic
            decision = WorkflowDecision(
                action="complete",
                reasoning="Default completion decision",
                confidence=0.5
            )
            
            if results_quality >= 0.8 and error_count == 0:
                decision.action = "complete"
                decision.reasoning = "High quality results achieved with no errors"
                decision.confidence = 0.9
            elif results_quality < 0.5 and error_count < 3:
                decision.action = "retry"
                decision.reasoning = "Low quality results, retry with different approach"
                decision.confidence = 0.7
                decision.estimated_duration_minutes = 10
            elif error_count >= 3:
                decision.action = "fail"
                decision.reasoning = "Multiple errors encountered, failing job"
                decision.confidence = 0.9
            else:
                # Determine best agent for handoff
                if job_status == "needs_analysis":
                    decision.action = "handoff"
                    decision.target_agent = "discovery_agent"
                    decision.reasoning = "Complex analysis needed, handoff to Discovery Agent"
                elif job_status == "needs_extraction":
                    decision.action = "handoff"
                    decision.target_agent = "html_extraction_agent"
                    decision.reasoning = "Content extraction needed, handoff to HTML Agent"
            
            return {
                "success": True,
                "decision": decision.model_dump(),
                "alternative_options": [opt for opt in available_options if opt != decision.action]
            }
            
        except Exception as e:
            self.logger.error(f"Error making workflow decision: {e}")
            return {"success": False, "error": str(e)}
    
    async def _coordinate_parallel_extraction(self, extraction_methods: List[str], 
                                            job_context: Dict[str, Any]) -> Dict[str, Any]:
        """SDK Tool: Coordinate parallel extraction using multiple agents"""
        try:
            parallel_plan = {
                "agents_involved": [],
                "estimated_completion_time": 0,
                "coordination_strategy": "parallel",
                "synchronization_points": []
            }
            
            # Map extraction methods to agents
            method_agent_map = {
                "html_parsing": "html_extraction_agent",
                "pdf_extraction": "pdf_analysis_agent", 
                "vision_processing": "vision_processing_agent"
            }
            
            for method in extraction_methods:
                if method in method_agent_map:
                    agent_id = method_agent_map[method]
                    parallel_plan["agents_involved"].append({
                        "agent_id": agent_id,
                        "method": method,
                        "estimated_duration": self._estimate_method_duration(method)
                    })
            
            # Calculate parallel execution time (max of individual times)
            if parallel_plan["agents_involved"]:
                max_duration = max(agent["estimated_duration"] for agent in parallel_plan["agents_involved"])
                parallel_plan["estimated_completion_time"] = max_duration + 2  # +2 for coordination overhead
            
            # Add synchronization points
            parallel_plan["synchronization_points"] = [
                "start_extraction",
                "collect_results", 
                "quality_assessment",
                "consolidation"
            ]
            
            return {
                "success": True,
                "parallel_plan": parallel_plan,
                "benefits": f"Parallel execution reduces time from {sum(agent['estimated_duration'] for agent in parallel_plan['agents_involved'])} to {parallel_plan['estimated_completion_time']} minutes"
            }
            
        except Exception as e:
            self.logger.error(f"Error coordinating parallel extraction: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_workflow_error(self, error_details: Dict[str, Any], 
                                   recovery_context: Dict[str, Any]) -> Dict[str, Any]:
        """SDK Tool: Handle workflow errors with intelligent recovery"""
        try:
            error_type = error_details.get("type", "unknown")
            error_stage = error_details.get("stage", "unknown")
            retry_count = recovery_context.get("retry_count", 0)
            max_retries = recovery_context.get("max_retries", 3)
            
            recovery_strategy = {
                "action": "fail",
                "reasoning": "No recovery strategy available",
                "alternative_approach": None,
                "estimated_recovery_time": 0
            }
            
            # Stage-specific error handling
            if error_stage == "analysis" and retry_count < max_retries:
                recovery_strategy.update({
                    "action": "retry_with_fallback",
                    "reasoning": "Analysis failed, try simpler approach",
                    "alternative_approach": "basic_html_extraction",
                    "estimated_recovery_time": 5
                })
            elif error_stage == "extraction" and retry_count < max_retries:
                recovery_strategy.update({
                    "action": "switch_method",
                    "reasoning": "Extraction method failed, try alternative",
                    "alternative_approach": "pdf_extraction" if "html" in error_type else "html_extraction",
                    "estimated_recovery_time": 10
                })
            elif error_type == "timeout":
                recovery_strategy.update({
                    "action": "reduce_scope",
                    "reasoning": "Timeout occurred, reduce extraction scope",
                    "alternative_approach": "sample_extraction",
                    "estimated_recovery_time": 3
                })
            
            return {
                "success": True,
                "recovery_strategy": recovery_strategy,
                "retry_recommended": recovery_strategy["action"] != "fail",
                "confidence": 0.8 if recovery_strategy["action"] != "fail" else 0.2
            }
            
        except Exception as e:
            self.logger.error(f"Error handling workflow error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _optimize_workflow_performance(self, historical_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """SDK Tool: Analyze and optimize workflow performance"""
        try:
            historical_data = historical_data or self.orchestration_metrics
            
            optimizations = []
            performance_insights = {}
            
            # Analyze success rates
            total_jobs = historical_data.get("total_jobs", 0)
            if total_jobs > 0:
                success_rate = historical_data.get("successful_jobs", 0) / total_jobs
                performance_insights["success_rate"] = success_rate
                
                if success_rate < 0.8:
                    optimizations.append("Improve error handling and recovery strategies")
                if success_rate < 0.6:
                    optimizations.append("Review agent selection and handoff decisions")
            
            # Analyze workflow timing
            avg_time = historical_data.get("average_workflow_time", 0)
            performance_insights["average_workflow_time"] = avg_time
            
            if avg_time > 30:  # 30 minutes
                optimizations.append("Consider more parallel processing opportunities")
            if avg_time > 60:  # 60 minutes
                optimizations.append("Implement workflow timeout and progressive fallback")
            
            # Analyze agent utilization
            agent_util = historical_data.get("agent_utilization", {})
            for agent, utilization in agent_util.items():
                if utilization > 0.9:
                    optimizations.append(f"Consider scaling {agent} - high utilization detected")
                elif utilization < 0.2:
                    optimizations.append(f"Review {agent} usage - low utilization detected")
            
            return {
                "success": True,
                "performance_insights": performance_insights,
                "optimization_recommendations": optimizations,
                "overall_health": "good" if len(optimizations) < 3 else "needs_improvement"
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing workflow performance: {e}")
            return {"success": False, "error": str(e)}
    
    # Helper methods
    
    def _analyze_url_patterns(self, url: str) -> Dict[str, Any]:
        """Analyze URL for complexity indicators"""
        domain = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()
        
        indicators = {
            "complexity_score": 0.5,  # Base complexity
            "government_domain": False,
            "likely_complex": False,
            "image_heavy": False,
            "pdf_heavy": False
        }
        
        # Government domain detection
        if any(tld in domain for tld in ['.gov', '.gov.uk', '.europa.eu', '.gc.ca', '.gov.au']):
            indicators["government_domain"] = True
            indicators["complexity_score"] += 0.3
        
        # Complex site indicators
        if any(keyword in domain or keyword in path for keyword in ['parliament', 'legislation', 'regulation', 'legal']):
            indicators["likely_complex"] = True
            indicators["complexity_score"] += 0.2
        
        # Content type indicators
        if any(keyword in path for keyword in ['pdf', 'document', 'download']):
            indicators["pdf_heavy"] = True
        
        if any(keyword in path for keyword in ['image', 'photo', 'media']):
            indicators["image_heavy"] = True
        
        return indicators
    
    def _estimate_success_rate(self, domain_indicators: Dict, stages: List[str]) -> float:
        """Estimate job success rate based on indicators and stages"""
        base_rate = 0.8  # 80% base success rate
        
        # Adjust based on complexity
        complexity = domain_indicators.get("complexity_score", 0.5)
        rate_adjustment = (1.0 - complexity) * 0.2  # Up to 20% adjustment
        
        # Adjust based on number of stages (more stages = slightly higher risk)
        stage_adjustment = max(0, (len(stages) - 3) * 0.05)  # 5% per extra stage
        
        final_rate = base_rate + rate_adjustment - stage_adjustment
        return max(0.3, min(0.95, final_rate))  # Clamp between 30% and 95%
    
    def _estimate_method_duration(self, method: str) -> int:
        """Estimate duration for extraction method in minutes"""
        durations = {
            "html_parsing": 3,
            "pdf_extraction": 8,
            "vision_processing": 12,
            "validation": 2
        }
        return durations.get(method, 5)