"""
Agent Coordination System
Manages multi-agent workflows, state synchronization, and inter-agent communication
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid

from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...models.extraction_models import ExtractionJob, ExtractionStatus, AgentMetrics
from ..llm_agents.base_agent import AgentRole


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running" 
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AgentState:
    """Current state of an agent"""
    agent_id: str
    agent_role: AgentRole
    status: str = "idle"  # idle, busy, error, offline
    current_job_id: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    queue_length: int = 0


@dataclass
class WorkflowStep:
    """A step in a workflow"""
    step_id: str
    agent_role: AgentRole
    task_description: str
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    priority: TaskPriority = TaskPriority.NORMAL
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Workflow:
    """A complete multi-agent workflow"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentCoordinator:
    """Coordinates multiple LLM agents and manages workflows"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.coordinator_id = f"coordinator_{uuid.uuid4().hex[:8]}"
        self.logger = logging.getLogger(f"{__name__}.{self.coordinator_id}")
        
        # State management
        self.agent_states: Dict[str, AgentState] = {}
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_queue: List[str] = []  # Queue of workflow IDs
        self.agent_capabilities: Dict[AgentRole, List[str]] = {}
        
        # Coordination settings
        self.max_concurrent_workflows = 10
        self.heartbeat_timeout = timedelta(minutes=5)
        self.step_timeout = timedelta(minutes=30)
        self.coordination_enabled = False
        
        # Performance tracking
        self.workflow_metrics: Dict[str, Any] = {
            "total_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "average_completion_time": 0.0,
            "agent_utilization": {}
        }
    
    async def start(self):
        """Start the agent coordinator"""
        if self.coordination_enabled:
            self.logger.warning("Agent coordinator is already running")
            return
        
        self.coordination_enabled = True
        self.logger.info(f"Starting agent coordinator: {self.coordinator_id}")
        
        # Subscribe to coordination messages
        await self._setup_message_subscriptions()
        
        # Start background tasks
        asyncio.create_task(self._workflow_executor())
        asyncio.create_task(self._agent_health_monitor())
        asyncio.create_task(self._performance_tracker())
        
        self.logger.info("Agent coordinator started successfully")
    
    async def stop(self):
        """Stop the agent coordinator"""
        self.coordination_enabled = False
        
        # Cancel running workflows
        for workflow_id in list(self.active_workflows.keys()):
            await self.cancel_workflow(workflow_id, reason="Coordinator shutdown")
        
        self.logger.info("Agent coordinator stopped")
    
    async def _setup_message_subscriptions(self):
        """Setup message broker subscriptions"""
        # Subscribe to agent health updates
        await self.broker.subscribe_channel(MessageType.AGENT_HEALTH_CHECK, self._handle_agent_health)
        
        # Subscribe to job completion messages
        await self.broker.subscribe_channel(MessageType.CONTENT_EXTRACTED, self._handle_job_completion)
        await self.broker.subscribe_channel(MessageType.JOB_FAILED, self._handle_job_failure)
        
        # Subscribe to workflow requests
        await self.broker.subscribe_channel(MessageType.WORKFLOW_REQUEST, self._handle_workflow_request)
    
    async def register_agent(self, agent_id: str, agent_role: AgentRole, capabilities: List[str]):
        """Register an agent with the coordinator"""
        agent_state = AgentState(
            agent_id=agent_id,
            agent_role=agent_role,
            status="idle",
            last_heartbeat=datetime.utcnow()
        )
        
        self.agent_states[agent_id] = agent_state
        self.agent_capabilities[agent_role] = capabilities
        
        self.logger.info(f"Registered agent: {agent_id} ({agent_role.value}) with capabilities: {capabilities}")
    
    async def create_extraction_workflow(self, url: str, extraction_config: Dict[str, Any]) -> str:
        """Create a complete regulation extraction workflow"""
        workflow_id = f"extraction_{uuid.uuid4().hex[:8]}"
        
        # Define workflow steps
        steps = [
            WorkflowStep(
                step_id=f"{workflow_id}_discovery",
                agent_role=AgentRole.DISCOVERY,
                task_description="Analyze website and determine extraction strategy",
                input_data={
                    "url": url,
                    "analysis_depth": extraction_config.get("analysis_depth", "standard")
                },
                priority=TaskPriority.NORMAL
            ),
            WorkflowStep(
                step_id=f"{workflow_id}_orchestration",
                agent_role=AgentRole.ORCHESTRATOR,
                task_description="Plan and coordinate extraction process",
                input_data={
                    "url": url,
                    "config": extraction_config
                },
                dependencies=[f"{workflow_id}_discovery"],
                priority=TaskPriority.NORMAL
            ),
            WorkflowStep(
                step_id=f"{workflow_id}_html_extraction",
                agent_role=AgentRole.HTML_EXTRACTOR,
                task_description="Extract content from HTML pages",
                input_data={
                    "url": url,
                    "extraction_strategy": "adaptive"
                },
                dependencies=[f"{workflow_id}_orchestration"],
                priority=TaskPriority.NORMAL
            ),
            WorkflowStep(
                step_id=f"{workflow_id}_content_validation",
                agent_role=AgentRole.CONTENT_VALIDATOR,
                task_description="Validate extracted content quality",
                input_data={
                    "validation_level": extraction_config.get("validation_level", "standard")
                },
                dependencies=[f"{workflow_id}_html_extraction"],
                priority=TaskPriority.NORMAL
            )
        ]
        
        # Add PDF analysis if needed
        if extraction_config.get("include_pdfs", True):
            steps.append(WorkflowStep(
                step_id=f"{workflow_id}_pdf_analysis",
                agent_role=AgentRole.PDF_ANALYZER,
                task_description="Analyze and extract content from PDF documents",
                input_data={
                    "url": url,
                    "ocr_enabled": extraction_config.get("ocr_enabled", True)
                },
                dependencies=[f"{workflow_id}_orchestration"],
                priority=TaskPriority.NORMAL
            ))
            
            # Update validation to wait for PDF analysis
            validation_step = next(s for s in steps if s.step_id.endswith("_content_validation"))
            validation_step.dependencies.append(f"{workflow_id}_pdf_analysis")
        
        # Add vision processing for images if enabled
        if extraction_config.get("include_images", False):
            steps.append(WorkflowStep(
                step_id=f"{workflow_id}_vision_processing",
                agent_role=AgentRole.VISION_PROCESSOR,
                task_description="Process images and visual content",
                input_data={
                    "url": url,
                    "image_analysis_depth": extraction_config.get("image_analysis_depth", "basic")
                },
                dependencies=[f"{workflow_id}_orchestration"],
                priority=TaskPriority.NORMAL
            ))
            
            # Update validation dependencies
            validation_step = next(s for s in steps if s.step_id.endswith("_content_validation"))
            validation_step.dependencies.append(f"{workflow_id}_vision_processing")
        
        # Create workflow
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Regulation Extraction: {url}",
            description=f"Complete extraction workflow for regulations from {url}",
            steps=steps,
            metadata={
                "url": url,
                "config": extraction_config,
                "created_by": "agent_coordinator"
            }
        )
        
        # Add to queue
        self.active_workflows[workflow_id] = workflow
        self.workflow_queue.append(workflow_id)
        
        self.logger.info(f"Created extraction workflow: {workflow_id} with {len(steps)} steps")
        
        return workflow_id
    
    async def create_custom_workflow(self, workflow_config: Dict[str, Any]) -> str:
        """Create a custom workflow from configuration"""
        workflow_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        steps = []
        for step_config in workflow_config.get("steps", []):
            step = WorkflowStep(
                step_id=step_config["step_id"],
                agent_role=AgentRole(step_config["agent_role"]),
                task_description=step_config["task_description"],
                input_data=step_config.get("input_data", {}),
                dependencies=step_config.get("dependencies", []),
                priority=TaskPriority(step_config.get("priority", "normal")),
                max_retries=step_config.get("max_retries", 3)
            )
            steps.append(step)
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=workflow_config.get("name", f"Custom Workflow {workflow_id}"),
            description=workflow_config.get("description", ""),
            steps=steps,
            metadata=workflow_config.get("metadata", {})
        )
        
        self.active_workflows[workflow_id] = workflow
        self.workflow_queue.append(workflow_id)
        
        self.logger.info(f"Created custom workflow: {workflow_id}")
        
        return workflow_id
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow"""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow = self.active_workflows[workflow_id]
        
        # Calculate progress
        completed_steps = len([s for s in workflow.steps if s.status == WorkflowStatus.COMPLETED])
        total_steps = len(workflow.steps)
        progress = completed_steps / total_steps if total_steps > 0 else 0.0
        workflow.progress = progress
        
        # Get step details
        step_details = []
        for step in workflow.steps:
            step_detail = {
                "step_id": step.step_id,
                "agent_role": step.agent_role.value,
                "task_description": step.task_description,
                "status": step.status.value,
                "dependencies": step.dependencies,
                "retry_count": step.retry_count,
                "error": step.error
            }
            
            if step.start_time:
                step_detail["start_time"] = step.start_time.isoformat()
            if step.end_time:
                step_detail["end_time"] = step.end_time.isoformat()
                step_detail["execution_time"] = (step.end_time - step.start_time).total_seconds()
            
            step_details.append(step_detail)
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "progress": progress,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "steps": step_details,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "metadata": workflow.metadata
        }
    
    async def cancel_workflow(self, workflow_id: str, reason: str = "User requested") -> bool:
        """Cancel a running workflow"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        # Cancel running steps
        for step in workflow.steps:
            if step.status == WorkflowStatus.RUNNING:
                step.status = WorkflowStatus.CANCELLED
                step.error = f"Cancelled: {reason}"
                step.end_time = datetime.utcnow()
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.utcnow()
        
        # Remove from queue if pending
        if workflow_id in self.workflow_queue:
            self.workflow_queue.remove(workflow_id)
        
        self.logger.info(f"Cancelled workflow: {workflow_id} - {reason}")
        
        return True
    
    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of agents"""
        if agent_id:
            if agent_id not in self.agent_states:
                return {"error": f"Agent {agent_id} not found"}
            
            agent_state = self.agent_states[agent_id]
            return {
                "agent_id": agent_state.agent_id,
                "agent_role": agent_state.agent_role.value,
                "status": agent_state.status,
                "current_job_id": agent_state.current_job_id,
                "last_heartbeat": agent_state.last_heartbeat.isoformat() if agent_state.last_heartbeat else None,
                "performance_metrics": agent_state.performance_metrics,
                "error_count": agent_state.error_count,
                "queue_length": agent_state.queue_length
            }
        else:
            # Return all agent statuses
            agents_status = {}
            for aid, state in self.agent_states.items():
                agents_status[aid] = {
                    "agent_role": state.agent_role.value,
                    "status": state.status,
                    "current_job_id": state.current_job_id,
                    "last_heartbeat": state.last_heartbeat.isoformat() if state.last_heartbeat else None,
                    "error_count": state.error_count,
                    "queue_length": state.queue_length
                }
            
            return {
                "total_agents": len(self.agent_states),
                "online_agents": len([s for s in self.agent_states.values() if s.status != "offline"]),
                "busy_agents": len([s for s in self.agent_states.values() if s.status == "busy"]),
                "agents": agents_status
            }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system performance metrics"""
        # Calculate current metrics
        total_workflows = len(self.active_workflows)
        completed_workflows = len([w for w in self.active_workflows.values() 
                                  if w.status == WorkflowStatus.COMPLETED])
        failed_workflows = len([w for w in self.active_workflows.values() 
                               if w.status == WorkflowStatus.FAILED])
        running_workflows = len([w for w in self.active_workflows.values() 
                                if w.status == WorkflowStatus.RUNNING])
        
        # Agent utilization
        agent_utilization = {}
        for agent_id, state in self.agent_states.items():
            utilization = 1.0 if state.status == "busy" else 0.0
            agent_utilization[agent_id] = {
                "role": state.agent_role.value,
                "utilization": utilization,
                "queue_length": state.queue_length,
                "error_rate": state.error_count / max(1, state.performance_metrics.get("jobs_processed", 1))
            }
        
        return {
            "coordinator_id": self.coordinator_id,
            "coordination_enabled": self.coordination_enabled,
            "workflows": {
                "total": total_workflows,
                "running": running_workflows,
                "completed": completed_workflows,
                "failed": failed_workflows,
                "queued": len(self.workflow_queue)
            },
            "agents": {
                "total_registered": len(self.agent_states),
                "online": len([s for s in self.agent_states.values() if s.status != "offline"]),
                "busy": len([s for s in self.agent_states.values() if s.status == "busy"]),
                "utilization": agent_utilization
            },
            "performance": {
                "max_concurrent_workflows": self.max_concurrent_workflows,
                "average_workflow_completion_time": self._calculate_avg_completion_time(),
                "system_load": running_workflows / self.max_concurrent_workflows
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _workflow_executor(self):
        """Background task to execute workflows"""
        while self.coordination_enabled:
            try:
                await self._process_workflow_queue()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Error in workflow executor: {e}")
                await asyncio.sleep(10)
    
    async def _process_workflow_queue(self):
        """Process workflows in the queue"""
        # Get currently running workflows
        running_count = len([w for w in self.active_workflows.values() 
                            if w.status == WorkflowStatus.RUNNING])
        
        # Start new workflows if under limit
        if running_count < self.max_concurrent_workflows and self.workflow_queue:
            workflow_id = self.workflow_queue.pop(0)
            
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                if workflow.status == WorkflowStatus.PENDING:
                    await self._start_workflow(workflow)
        
        # Process running workflows
        for workflow in list(self.active_workflows.values()):
            if workflow.status == WorkflowStatus.RUNNING:
                await self._process_workflow_steps(workflow)
    
    async def _start_workflow(self, workflow: Workflow):
        """Start executing a workflow"""
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        self.logger.info(f"Starting workflow: {workflow.workflow_id}")
        
        # Find ready steps (no dependencies)
        ready_steps = [step for step in workflow.steps 
                      if step.status == WorkflowStatus.PENDING and not step.dependencies]
        
        # Start ready steps
        for step in ready_steps:
            await self._start_workflow_step(step)
    
    async def _process_workflow_steps(self, workflow: Workflow):
        """Process steps in a running workflow"""
        # Check for completed/failed steps and start dependent steps
        completed_steps = [s.step_id for s in workflow.steps 
                          if s.status == WorkflowStatus.COMPLETED]
        
        # Find steps that can now run
        ready_steps = []
        for step in workflow.steps:
            if (step.status == WorkflowStatus.PENDING and 
                all(dep in completed_steps for dep in step.dependencies)):
                ready_steps.append(step)
        
        # Start ready steps
        for step in ready_steps:
            await self._start_workflow_step(step)
        
        # Check if workflow is complete
        all_complete = all(step.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] 
                          for step in workflow.steps)
        
        if all_complete:
            await self._complete_workflow(workflow)
    
    async def _start_workflow_step(self, step: WorkflowStep):
        """Start executing a workflow step"""
        # Find available agent for this role
        agent_id = await self._find_available_agent(step.agent_role)
        
        if not agent_id:
            self.logger.warning(f"No available agent for role {step.agent_role.value}, step {step.step_id} waiting")
            return
        
        step.status = WorkflowStatus.RUNNING
        step.start_time = datetime.utcnow()
        
        # Update agent state
        if agent_id in self.agent_states:
            self.agent_states[agent_id].status = "busy"
            self.agent_states[agent_id].current_job_id = step.step_id
        
        # Send job to agent
        job_message = await create_message(
            message_type=MessageType.JOB_CREATED,
            sender=self.coordinator_id,
            recipient=agent_id,
            payload={
                "job_id": step.step_id,
                "workflow_id": step.step_id.split("_")[0] + "_" + step.step_id.split("_")[1],  # Extract workflow ID
                "task_description": step.task_description,
                "input_data": step.input_data,
                "priority": step.priority.value,
                "timeout": self.step_timeout.total_seconds()
            },
            correlation_id=step.step_id
        )
        
        await self.broker.publish(job_message)
        
        self.logger.info(f"Started step {step.step_id} on agent {agent_id}")
    
    async def _find_available_agent(self, role: AgentRole) -> Optional[str]:
        """Find an available agent for the given role"""
        suitable_agents = [aid for aid, state in self.agent_states.items() 
                          if state.agent_role == role and state.status == "idle"]
        
        if not suitable_agents:
            return None
        
        # Select agent with lowest queue length / best performance
        best_agent = min(suitable_agents, 
                        key=lambda aid: (self.agent_states[aid].queue_length, 
                                       self.agent_states[aid].error_count))
        
        return best_agent
    
    async def _complete_workflow(self, workflow: Workflow):
        """Complete a workflow"""
        # Determine final status
        failed_steps = [s for s in workflow.steps if s.status == WorkflowStatus.FAILED]
        cancelled_steps = [s for s in workflow.steps if s.status == WorkflowStatus.CANCELLED]
        
        if cancelled_steps:
            workflow.status = WorkflowStatus.CANCELLED
        elif failed_steps:
            workflow.status = WorkflowStatus.FAILED
        else:
            workflow.status = WorkflowStatus.COMPLETED
        
        workflow.completed_at = datetime.utcnow()
        
        # Update metrics
        self.workflow_metrics["total_workflows"] += 1
        if workflow.status == WorkflowStatus.COMPLETED:
            self.workflow_metrics["completed_workflows"] += 1
        elif workflow.status == WorkflowStatus.FAILED:
            self.workflow_metrics["failed_workflows"] += 1
        
        # Calculate completion time
        if workflow.started_at:
            completion_time = (workflow.completed_at - workflow.started_at).total_seconds()
            # Update rolling average
            current_avg = self.workflow_metrics["average_completion_time"]
            total_completed = self.workflow_metrics["completed_workflows"]
            if total_completed > 1:
                self.workflow_metrics["average_completion_time"] = (
                    (current_avg * (total_completed - 1) + completion_time) / total_completed
                )
            else:
                self.workflow_metrics["average_completion_time"] = completion_time
        
        self.logger.info(f"Completed workflow: {workflow.workflow_id} with status: {workflow.status.value}")
        
        # Send completion notification
        completion_message = await create_message(
            message_type=MessageType.WORKFLOW_COMPLETED,
            sender=self.coordinator_id,
            recipient="system",
            payload={
                "workflow_id": workflow.workflow_id,
                "status": workflow.status.value,
                "completion_time": completion_time if workflow.started_at else 0,
                "total_steps": len(workflow.steps),
                "successful_steps": len([s for s in workflow.steps if s.status == WorkflowStatus.COMPLETED])
            }
        )
        
        await self.broker.publish(completion_message)
    
    async def _agent_health_monitor(self):
        """Monitor agent health and update states"""
        while self.coordination_enabled:
            try:
                current_time = datetime.utcnow()
                
                # Check for offline agents
                for agent_id, state in list(self.agent_states.items()):
                    if state.last_heartbeat:
                        time_since_heartbeat = current_time - state.last_heartbeat
                        if time_since_heartbeat > self.heartbeat_timeout:
                            if state.status != "offline":
                                self.logger.warning(f"Agent {agent_id} appears offline - no heartbeat for {time_since_heartbeat}")
                                state.status = "offline"
                                state.current_job_id = None
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in agent health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _performance_tracker(self):
        """Track system performance metrics"""
        while self.coordination_enabled:
            try:
                # Update agent utilization metrics
                for agent_id, state in self.agent_states.items():
                    role = state.agent_role.value
                    
                    if role not in self.workflow_metrics["agent_utilization"]:
                        self.workflow_metrics["agent_utilization"][role] = {
                            "total_time": 0.0,
                            "busy_time": 0.0,
                            "utilization": 0.0
                        }
                    
                    # Simple utilization tracking
                    if state.status == "busy":
                        self.workflow_metrics["agent_utilization"][role]["busy_time"] += 30  # 30 second intervals
                    
                    self.workflow_metrics["agent_utilization"][role]["total_time"] += 30
                    
                    # Calculate utilization percentage
                    total = self.workflow_metrics["agent_utilization"][role]["total_time"]
                    busy = self.workflow_metrics["agent_utilization"][role]["busy_time"]
                    self.workflow_metrics["agent_utilization"][role]["utilization"] = (busy / total) if total > 0 else 0.0
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in performance tracker: {e}")
                await asyncio.sleep(60)
    
    def _calculate_avg_completion_time(self) -> float:
        """Calculate average workflow completion time"""
        return self.workflow_metrics.get("average_completion_time", 0.0)
    
    # Message handlers
    async def _handle_agent_health(self, message: Message):
        """Handle agent health check messages"""
        payload = message.payload
        agent_id = payload.get("agent_id")
        
        if agent_id and agent_id in self.agent_states:
            state = self.agent_states[agent_id]
            state.last_heartbeat = datetime.utcnow()
            
            # Update performance metrics if provided
            if "metrics" in payload:
                metrics = payload["metrics"]
                state.performance_metrics.update(metrics)
            
            # Update status if changed
            agent_status = payload.get("status", "idle")
            if state.status == "offline" and agent_status != "offline":
                state.status = "idle"  # Agent came back online
                self.logger.info(f"Agent {agent_id} is back online")
    
    async def _handle_job_completion(self, message: Message):
        """Handle job completion messages"""
        payload = message.payload
        job_id = payload.get("job_id")
        agent_id = message.sender
        
        # Find the workflow step
        step = None
        workflow = None
        for w in self.active_workflows.values():
            for s in w.steps:
                if s.step_id == job_id:
                    step = s
                    workflow = w
                    break
            if step:
                break
        
        if step and workflow:
            step.status = WorkflowStatus.COMPLETED
            step.end_time = datetime.utcnow()
            step.result = payload
            
            # Update agent state
            if agent_id in self.agent_states:
                self.agent_states[agent_id].status = "idle"
                self.agent_states[agent_id].current_job_id = None
            
            self.logger.info(f"Step {step.step_id} completed successfully")
        else:
            self.logger.warning(f"Received completion for unknown job: {job_id}")
    
    async def _handle_job_failure(self, message: Message):
        """Handle job failure messages"""
        payload = message.payload
        job_id = payload.get("job_id")
        agent_id = message.sender
        error = payload.get("error", "Unknown error")
        
        # Find the workflow step
        step = None
        workflow = None
        for w in self.active_workflows.values():
            for s in w.steps:
                if s.step_id == job_id:
                    step = s
                    workflow = w
                    break
            if step:
                break
        
        if step and workflow:
            step.retry_count += 1
            step.error = error
            
            # Retry if under limit
            if step.retry_count < step.max_retries:
                step.status = WorkflowStatus.PENDING
                self.logger.warning(f"Step {step.step_id} failed (attempt {step.retry_count}), retrying: {error}")
            else:
                step.status = WorkflowStatus.FAILED
                step.end_time = datetime.utcnow()
                self.logger.error(f"Step {step.step_id} failed permanently after {step.retry_count} attempts: {error}")
            
            # Update agent state
            if agent_id in self.agent_states:
                self.agent_states[agent_id].status = "idle"
                self.agent_states[agent_id].current_job_id = None
                self.agent_states[agent_id].error_count += 1
        else:
            self.logger.warning(f"Received failure for unknown job: {job_id}")
    
    async def _handle_workflow_request(self, message: Message):
        """Handle workflow creation requests"""
        payload = message.payload
        request_type = payload.get("type", "extraction")
        
        if request_type == "extraction":
            url = payload.get("url")
            config = payload.get("config", {})
            
            if url:
                workflow_id = await self.create_extraction_workflow(url, config)
                
                # Send response
                response = await create_message(
                    message_type=MessageType.WORKFLOW_CREATED,
                    sender=self.coordinator_id,
                    recipient=message.sender,
                    payload={
                        "workflow_id": workflow_id,
                        "status": "created"
                    },
                    correlation_id=message.correlation_id
                )
                
                await self.broker.publish(response)
            else:
                self.logger.error("Workflow request missing required URL")
        else:
            self.logger.warning(f"Unknown workflow request type: {request_type}")