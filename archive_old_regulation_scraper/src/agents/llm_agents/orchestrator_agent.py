"""
Orchestrator LLM Agent
Central coordination system powered by GPT-4 for managing extraction workflows
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

from .base_agent import BaseLLMAgent, AgentRole, AgentContext
from ...infrastructure.message_broker import MessageType
from ...models.extraction_models import ExtractionJob, ExtractionStatus, ExtractionMethod
from ...models.regulation_models import Regulation


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Available agent types"""
    DISCOVERY = "discovery"
    HTML_EXTRACTOR = "html_extractor"
    PDF_ANALYZER = "pdf_analyzer"
    VISION_PROCESSOR = "vision_processor"
    CONTENT_VALIDATOR = "content_validator"


@dataclass
class JobPlan:
    """Execution plan for a job"""
    job_id: str
    url: str
    stages: List[str] = field(default_factory=list)
    current_stage: int = 0
    assigned_agents: Dict[str, str] = field(default_factory=dict)
    stage_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    estimated_duration: Optional[int] = None


@dataclass
class WorkflowContext:
    """Context for workflow execution"""
    job_plan: JobPlan
    discovery_analysis: Optional[Dict[str, Any]] = None
    extraction_results: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: Optional[Dict[str, Any]] = None
    error_history: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


class OrchestratorAgent(BaseLLMAgent):
    """Intelligent orchestrator powered by GPT-4"""
    
    def __init__(self, broker):
        system_prompt = """You are the Orchestrator Agent, the central intelligence that coordinates the entire regulation extraction system.

Your primary responsibilities:
1. Analyze extraction requests and determine optimal strategies
2. Coordinate multiple specialized agents (Discovery, HTML, PDF, Vision, Validation)
3. Make intelligent routing decisions based on website characteristics
4. Handle error recovery and adaptive strategy adjustment
5. Optimize extraction workflows for maximum efficiency and accuracy
6. Ensure quality and completeness of extracted regulation data

Available specialist agents:
- Discovery Agent: Analyzes websites and recommends extraction strategies
- HTML Extraction Agent: Extracts content from HTML pages using DOM analysis
- PDF Analysis Agent: Processes PDF documents with OCR capabilities
- Vision Processing Agent: Handles images and complex visual layouts
- Content Validation Agent: Validates and ensures quality of extracted data

Your decision-making process should:
1. Receive extraction requests and assess requirements
2. Delegate initial analysis to Discovery Agent
3. Based on discovery results, route jobs to appropriate extraction agents
4. Coordinate parallel processing when beneficial
5. Handle errors intelligently with adaptive retry strategies
6. Validate final results before completion
7. Learn from patterns to optimize future extractions

Always provide clear reasoning for your decisions and maintain awareness of resource constraints and processing priorities."""

        super().__init__(
            agent_id="orchestrator_agent",
            agent_role=AgentRole.ORCHESTRATOR,
            broker=broker,
            system_prompt=system_prompt,
            temperature=0.2  # Slightly higher for creative problem solving
        )
        
        # Job management
        self.active_jobs: Dict[str, WorkflowContext] = {}
        self.completed_jobs: Dict[str, WorkflowContext] = {}
        self.job_queue: List[str] = []
        
        # Agent availability tracking
        self.available_agents: Dict[AgentType, Set[str]] = {
            AgentType.DISCOVERY: {"discovery_llm_agent"},
            AgentType.HTML_EXTRACTOR: {"html_extraction_agent"},
            AgentType.PDF_ANALYZER: {"pdf_analysis_agent"},
            AgentType.VISION_PROCESSOR: {"vision_processing_agent"},
            AgentType.CONTENT_VALIDATOR: {"content_validation_agent"}
        }
        
        # Performance tracking
        self.job_statistics = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "average_processing_time": 0.0,
            "agent_utilization": {}
        }
    
    async def _register_tools(self):
        """Register orchestration tools"""
        
        # Job planning and strategy tool
        self.register_tool(
            name="create_job_plan",
            function=self._create_job_plan,
            description="Create an execution plan for a regulation extraction job",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target URL for extraction"},
                    "job_requirements": {
                        "type": "object",
                        "description": "Specific requirements and constraints",
                        "properties": {
                            "max_documents": {"type": "integer"},
                            "document_types": {"type": "array", "items": {"type": "string"}},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                        }
                    },
                    "suggested_strategy": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Suggested extraction methods from discovery"
                    }
                },
                "required": ["url"]
            }
        )
        
        # Agent delegation tool
        self.register_tool(
            name="delegate_to_agent",
            function=self._delegate_to_agent,
            description="Delegate a task to a specialist agent",
            parameters={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": ["discovery", "html_extractor", "pdf_analyzer", "vision_processor", "content_validator"]
                    },
                    "job_id": {"type": "string"},
                    "task_data": {
                        "type": "object",
                        "description": "Task-specific data and instructions"
                    }
                },
                "required": ["agent_type", "job_id", "task_data"]
            }
        )
        
        # Workflow coordination tool
        self.register_tool(
            name="update_job_status",
            function=self._update_job_status,
            description="Update job status and move to next stage",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "analyzing", "extracting", "validating", "completed", "failed"]
                    },
                    "stage_result": {
                        "type": "object",
                        "description": "Results from completed stage"
                    }
                },
                "required": ["job_id", "status"]
            }
        )
        
        # Error handling and recovery tool
        self.register_tool(
            name="handle_job_error",
            function=self._handle_job_error,
            description="Handle job errors and determine recovery strategy",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "error_details": {
                        "type": "object",
                        "description": "Error information and context"
                    },
                    "recovery_options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Potential recovery strategies"
                    }
                },
                "required": ["job_id", "error_details"]
            }
        )
        
        # Performance optimization tool
        self.register_tool(
            name="optimize_workflow",
            function=self._optimize_workflow,
            description="Analyze and optimize workflow performance",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "performance_data": {
                        "type": "object",
                        "description": "Performance metrics and bottlenecks"
                    }
                },
                "required": ["job_id"]
            }
        )
    
    async def _handle_job_request(self, message, context: AgentContext):
        """Handle new job requests"""
        try:
            url = message.payload.get('url')
            job_requirements = message.payload.get('requirements', {})
            
            if not url:
                await self._send_error_response(message, "No URL provided")
                return
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            self.logger.info(f"Received extraction request for {url} (Job: {job_id})")
            
            # Create initial job context
            job_plan = JobPlan(job_id=job_id, url=url)
            workflow_context = WorkflowContext(job_plan=job_plan)
            self.active_jobs[job_id] = workflow_context
            
            # Use GPT-4 to analyze the request and create execution plan
            planning_prompt = f"""A new regulation extraction job has been received:

URL: {url}
Job ID: {job_id}
Requirements: {json.dumps(job_requirements, indent=2)}

Please analyze this request and create an optimal execution plan. Consider:
1. What type of website this likely is based on the URL
2. What extraction challenges we might face
3. Which agents should be involved and in what order
4. Any special considerations for this domain/jurisdiction

Create a job plan that maximizes success rate and efficiency."""

            # Generate response using available tools
            response = await self.generate_response(
                user_message=planning_prompt,
                context=context,
                use_tools=True
            )
            
            # Update job statistics
            self.job_statistics["total_jobs"] += 1
            
            self.logger.info(f"Created execution plan for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling job request: {e}")
            await self._send_error_response(message, str(e))
    
    async def _handle_analysis_result(self, message, context: AgentContext):
        """Handle discovery analysis results"""
        try:
            job_id = message.payload.get('job_id')
            analysis = message.payload.get('analysis', {})
            
            if job_id not in self.active_jobs:
                self.logger.warning(f"Received analysis for unknown job: {job_id}")
                return
            
            workflow_context = self.active_jobs[job_id]
            workflow_context.discovery_analysis = analysis
            
            self.logger.info(f"Received discovery analysis for job {job_id}")
            
            # Use GPT-4 to analyze the discovery results and plan next steps
            analysis_prompt = f"""Discovery analysis completed for job {job_id}:

Discovery Results:
{json.dumps(analysis, indent=2)}

Based on this analysis, please:
1. Assess the extraction feasibility and expected success rate
2. Determine which extraction agents should be deployed
3. Plan the extraction sequence and any parallel processing opportunities
4. Update the job status and delegate to appropriate agents
5. Identify any potential challenges or special handling needed

Use your tools to coordinate the next phase of extraction."""

            # Generate coordination response
            response = await self.generate_response(
                user_message=analysis_prompt,
                context=context,
                use_tools=True
            )
            
        except Exception as e:
            self.logger.error(f"Error handling analysis result: {e}")
            # Handle error through the error recovery system
            if job_id:
                await self._handle_job_error(job_id, {"error": str(e), "stage": "analysis"})
    
    async def _handle_content_result(self, message, context: AgentContext):
        """Handle content extraction results"""
        try:
            job_id = message.payload.get('job_id')
            content_results = message.payload.get('results', {})
            agent_id = message.payload.get('agent_id')
            
            if job_id not in self.active_jobs:
                self.logger.warning(f"Received content for unknown job: {job_id}")
                return
            
            workflow_context = self.active_jobs[job_id]
            workflow_context.extraction_results.append({
                "agent_id": agent_id,
                "results": content_results,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.logger.info(f"Received extraction results from {agent_id} for job {job_id}")
            
            # Use GPT-4 to evaluate results and determine next actions
            evaluation_prompt = f"""Extraction results received for job {job_id} from agent {agent_id}:

Results Summary:
{json.dumps(content_results, indent=2)}

Current Job Context:
- Discovery Analysis: {json.dumps(workflow_context.discovery_analysis, indent=2) if workflow_context.discovery_analysis else 'None'}
- Previous Results: {len(workflow_context.extraction_results)} agents completed

Please evaluate these results and determine:
1. Quality and completeness of the extracted content
2. Whether additional extraction agents are needed
3. If results are ready for validation or need more processing
4. Next steps in the workflow

Use your tools to coordinate the appropriate next actions."""

            # Generate coordination response
            response = await self.generate_response(
                user_message=evaluation_prompt,
                context=context,
                use_tools=True
            )
            
        except Exception as e:
            self.logger.error(f"Error handling content result: {e}")
            if job_id:
                await self._handle_job_error(job_id, {"error": str(e), "stage": "extraction"})
    
    async def _create_job_plan(self, url: str, job_requirements: Dict[str, Any] = None, 
                              suggested_strategy: List[str] = None) -> Dict[str, Any]:
        """Tool: Create execution plan for a job"""
        try:
            job_requirements = job_requirements or {}
            suggested_strategy = suggested_strategy or []
            
            # Determine stages based on strategy
            stages = ["discovery"]  # Always start with discovery
            
            if "html_parsing" in suggested_strategy:
                stages.append("html_extraction")
            if "pdf_extraction" in suggested_strategy:
                stages.append("pdf_analysis")
            if "computer_vision" in suggested_strategy:
                stages.append("vision_processing")
            
            # Always include validation
            stages.append("validation")
            
            # Estimate duration based on complexity
            base_duration = 60  # 1 minute base
            duration_multipliers = {
                "discovery": 1.0,
                "html_extraction": 1.5,
                "pdf_analysis": 2.0,
                "vision_processing": 3.0,
                "validation": 0.5
            }
            
            estimated_duration = sum(base_duration * duration_multipliers.get(stage, 1.0) 
                                   for stage in stages)
            
            return {
                "stages": stages,
                "estimated_duration": int(estimated_duration),
                "priority": job_requirements.get("priority", "medium"),
                "resource_requirements": {
                    "cpu_intensive": "vision_processing" in stages,
                    "network_heavy": len(stages) > 3,
                    "memory_usage": "high" if "pdf_analysis" in stages else "medium"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating job plan: {e}")
            return {"error": str(e)}
    
    async def _delegate_to_agent(self, agent_type: str, job_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Delegate task to specialist agent"""
        try:
            # Map agent type to queue name
            agent_queues = {
                "discovery": "discovery_agent",
                "html_extractor": "html_extraction_agent",
                "pdf_analyzer": "pdf_analysis_agent", 
                "vision_processor": "vision_processing_agent",
                "content_validator": "content_validation_agent"
            }
            
            queue_name = agent_queues.get(agent_type)
            if not queue_name:
                return {"error": f"Unknown agent type: {agent_type}"}
            
            # Create task message
            task_message = {
                "job_id": job_id,
                "task_type": agent_type,
                "task_data": task_data,
                "timestamp": datetime.utcnow().isoformat(),
                "orchestrator_id": self.agent_id
            }
            
            # Send to agent queue
            from ...infrastructure.message_broker import create_message
            message = await create_message(
                message_type=MessageType.JOB_CREATED,
                sender=self.agent_id,
                recipient=queue_name,
                payload=task_message,
                correlation_id=job_id
            )
            
            await self.broker.publish(message)
            
            self.logger.info(f"Delegated {agent_type} task for job {job_id}")
            
            return {"status": "delegated", "agent": agent_type, "queue": queue_name}
            
        except Exception as e:
            self.logger.error(f"Error delegating to agent: {e}")
            return {"error": str(e)}
    
    async def _update_job_status(self, job_id: str, status: str, stage_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tool: Update job status and progress"""
        try:
            if job_id not in self.active_jobs:
                return {"error": f"Job {job_id} not found"}
            
            workflow_context = self.active_jobs[job_id]
            job_plan = workflow_context.job_plan
            
            # Update stage results if provided
            if stage_result:
                current_stage = job_plan.stages[job_plan.current_stage] if job_plan.current_stage < len(job_plan.stages) else "unknown"
                job_plan.stage_results[current_stage] = stage_result
            
            # Move to next stage if appropriate
            if status in ["completed"] and job_plan.current_stage < len(job_plan.stages) - 1:
                job_plan.current_stage += 1
                next_stage = job_plan.stages[job_plan.current_stage]
                self.logger.info(f"Job {job_id} moved to stage: {next_stage}")
            
            # Handle job completion
            if status == "completed" and job_plan.current_stage >= len(job_plan.stages) - 1:
                # Move to completed jobs
                self.completed_jobs[job_id] = workflow_context
                del self.active_jobs[job_id]
                
                self.job_statistics["successful_jobs"] += 1
                self.logger.info(f"Job {job_id} completed successfully")
                
                # Send completion notification
                await self._send_job_completion_notification(job_id, workflow_context)
            
            # Handle job failure
            elif status == "failed":
                workflow_context.error_history.append(f"Job failed at stage: {status}")
                self.job_statistics["failed_jobs"] += 1
                
                # Attempt recovery if retries available
                if workflow_context.retry_count < workflow_context.max_retries:
                    workflow_context.retry_count += 1
                    self.logger.info(f"Retrying job {job_id} (attempt {workflow_context.retry_count})")
                    # Reset to previous stage for retry
                    job_plan.current_stage = max(0, job_plan.current_stage - 1)
                else:
                    # Move to completed with failure status
                    self.completed_jobs[job_id] = workflow_context
                    del self.active_jobs[job_id]
                    self.logger.error(f"Job {job_id} failed after {workflow_context.retry_count} retries")
            
            return {
                "job_id": job_id,
                "status": status,
                "current_stage": job_plan.current_stage,
                "total_stages": len(job_plan.stages),
                "retry_count": workflow_context.retry_count
            }
            
        except Exception as e:
            self.logger.error(f"Error updating job status: {e}")
            return {"error": str(e)}
    
    async def _handle_job_error(self, job_id: str, error_details: Dict[str, Any], 
                               recovery_options: List[str] = None) -> Dict[str, Any]:
        """Tool: Handle job errors and recovery"""
        try:
            if job_id not in self.active_jobs:
                return {"error": f"Job {job_id} not found"}
            
            workflow_context = self.active_jobs[job_id]
            error_message = error_details.get("error", "Unknown error")
            stage = error_details.get("stage", "unknown")
            
            workflow_context.error_history.append(f"{stage}: {error_message}")
            
            self.logger.warning(f"Error in job {job_id} at stage {stage}: {error_message}")
            
            # Determine recovery strategy
            recovery_actions = []
            
            if workflow_context.retry_count < workflow_context.max_retries:
                recovery_actions.append("retry_current_stage")
            
            if stage == "discovery":
                recovery_actions.append("fallback_basic_extraction")
            elif stage == "extraction":
                recovery_actions.append("try_alternative_method")
                recovery_actions.append("reduce_scope")
            
            # Apply recovery strategy
            recovery_strategy = recovery_options[0] if recovery_options else recovery_actions[0] if recovery_actions else "fail_job"
            
            if recovery_strategy == "retry_current_stage":
                workflow_context.retry_count += 1
                # Keep current stage for retry
                return {"action": "retry", "retry_count": workflow_context.retry_count}
            
            elif recovery_strategy == "fallback_basic_extraction":
                # Modify job plan for basic HTML extraction only
                job_plan = workflow_context.job_plan
                job_plan.stages = ["discovery", "html_extraction", "validation"]
                job_plan.current_stage = 1  # Skip to HTML extraction
                return {"action": "fallback", "new_stages": job_plan.stages}
            
            elif recovery_strategy == "try_alternative_method":
                # Switch extraction method
                return {"action": "switch_method", "stage": stage}
            
            else:
                # Fail the job
                await self._update_job_status(job_id, "failed", {"error": error_message})
                return {"action": "job_failed", "reason": error_message}
            
        except Exception as e:
            self.logger.error(f"Error in error handling: {e}")
            return {"error": str(e)}
    
    async def _optimize_workflow(self, job_id: str, performance_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tool: Optimize workflow performance"""
        try:
            performance_data = performance_data or {}
            
            # Analyze current performance metrics
            optimizations = []
            
            # Check agent utilization
            agent_stats = self.job_statistics.get("agent_utilization", {})
            for agent_type, utilization in agent_stats.items():
                if utilization > 0.9:  # Over 90% utilization
                    optimizations.append(f"Consider scaling {agent_type} agents")
                elif utilization < 0.3:  # Under 30% utilization
                    optimizations.append(f"Reduce {agent_type} agent allocation")
            
            # Check processing times
            avg_time = self.job_statistics.get("average_processing_time", 0)
            if avg_time > 300:  # Over 5 minutes
                optimizations.append("Consider parallel processing for complex jobs")
            
            # Success rate optimization
            success_rate = (self.job_statistics["successful_jobs"] / 
                          max(1, self.job_statistics["total_jobs"]))
            
            if success_rate < 0.8:  # Below 80% success rate
                optimizations.append("Review error patterns and improve retry strategies")
            
            return {
                "job_id": job_id,
                "current_performance": {
                    "success_rate": success_rate,
                    "average_processing_time": avg_time,
                    "total_jobs": self.job_statistics["total_jobs"]
                },
                "optimizations": optimizations,
                "recommendations": self._generate_performance_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing workflow: {e}")
            return {"error": str(e)}
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        total_jobs = self.job_statistics["total_jobs"]
        if total_jobs == 0:
            return ["Insufficient data for recommendations"]
        
        success_rate = self.job_statistics["successful_jobs"] / total_jobs
        
        if success_rate < 0.7:
            recommendations.append("Implement more robust error handling and retry logic")
        
        if success_rate < 0.5:
            recommendations.append("Review and improve agent coordination strategies")
        
        recommendations.append("Monitor agent performance metrics for optimization opportunities")
        recommendations.append("Implement caching for frequently accessed content")
        
        return recommendations
    
    async def _send_job_completion_notification(self, job_id: str, workflow_context: WorkflowContext):
        """Send job completion notification"""
        try:
            completion_data = {
                "job_id": job_id,
                "url": workflow_context.job_plan.url,
                "status": "completed",
                "processing_time": (datetime.utcnow() - workflow_context.job_plan.created_at).total_seconds(),
                "stages_completed": len(workflow_context.job_plan.stage_results),
                "total_results": len(workflow_context.extraction_results),
                "retry_count": workflow_context.retry_count
            }
            
            # Send to API or notification system
            await self._send_response(
                message_type=MessageType.JOB_COMPLETED,
                recipient="api_gateway",
                payload=completion_data,
                correlation_id=job_id
            )
            
            self.logger.info(f"Sent completion notification for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending completion notification: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "orchestrator_id": self.agent_id,
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "job_queue_size": len(self.job_queue),
            "statistics": self.job_statistics,
            "agent_availability": {
                agent_type.value: len(agents) 
                for agent_type, agents in self.available_agents.items()
            },
            "system_health": "healthy" if self.is_running else "stopped"
        }