"""
SDK-Based LLM Agent
Modern OpenAI Agents SDK implementation for the regulation scraping system
"""
import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

from agents import Agent, Runner, Session
from agents.tools import function_tool
from agents.guardrails import GuardrailFunction
from pydantic import BaseModel

from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...config.config_manager import get_config
from ...models.extraction_models import AgentMetrics
from .base_agent import AgentRole, AgentContext, ToolResult, ToolCallStatus


class SDKAgentStatus(str, Enum):
    """SDK Agent status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    IDLE = "idle"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class SDKAgentContext:
    """Enhanced context for SDK agents"""
    session_id: str
    correlation_id: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    session: Optional[Session] = None
    handoff_context: Dict[str, Any] = field(default_factory=dict)


class BaseSDKAgent:
    """Base class for OpenAI Agents SDK-powered agents"""
    
    def __init__(
        self, 
        agent_id: str,
        agent_role: AgentRole,
        broker: MessageBroker,
        instructions: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.broker = broker
        self.instructions = instructions
        
        # Configuration
        self.config = get_config()
        self.openai_config = self.config.openai
        
        # Model settings
        self.model = model or self.openai_config.default_model
        self.temperature = temperature or self.openai_config.temperature
        self.max_tokens = max_tokens or self.openai_config.max_tokens
        
        # SDK Agent instance (will be created in _initialize_agent)
        self.sdk_agent: Optional[Agent] = None
        self.runner = Runner()
        
        # State management
        self.status = SDKAgentStatus.INITIALIZING
        self.current_context: Optional[SDKAgentContext] = None
        self.active_sessions: Dict[str, Session] = {}
        
        # Tools and capabilities
        self.tools: List[Callable] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.handoff_agents: List[Agent] = []
        self.guardrails: List[GuardrailFunction] = []
        
        # Performance tracking
        self.metrics = AgentMetrics(
            agent_id=agent_id,
            agent_type=agent_role.value
        )
        
        # Logging
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
        
    async def start(self):
        """Start the SDK-based agent"""
        if self.status == SDKAgentStatus.READY:
            self.logger.warning(f"Agent {self.agent_id} is already running")
            return
        
        try:
            self.status = SDKAgentStatus.INITIALIZING
            self.logger.info(f"Starting SDK agent: {self.agent_id} ({self.agent_role.value})")
            
            # Initialize tools
            await self._register_tools()
            
            # Initialize SDK agent
            await self._initialize_agent()
            
            # Setup message subscriptions
            await self._setup_message_subscriptions()
            
            # Start message processing
            await self._start_message_processing()
            
            self.status = SDKAgentStatus.READY
            self.logger.info(f"SDK agent {self.agent_id} is ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start SDK agent {self.agent_id}: {e}")
            self.status = SDKAgentStatus.ERROR
            raise
    
    async def stop(self):
        """Stop the SDK agent"""
        self.status = SDKAgentStatus.STOPPED
        
        # Close active sessions
        for session in self.active_sessions.values():
            try:
                # Clean up session resources if needed
                pass
            except Exception as e:
                self.logger.warning(f"Error closing session: {e}")
        
        self.active_sessions.clear()
        self.logger.info(f"Stopped SDK agent: {self.agent_id}")
    
    async def _initialize_agent(self):
        """Initialize the OpenAI Agents SDK agent"""
        try:
            # Create SDK agent with tools and configuration
            self.sdk_agent = Agent(
                name=self.agent_id,
                instructions=self.instructions,
                model=self.model,
                tools=self.tools,
                handoffs=self.handoff_agents,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Add guardrails if enabled
            if self.openai_config.guardrails_enabled and self.guardrails:
                for guardrail in self.guardrails:
                    self.sdk_agent.add_guardrail(guardrail)
            
            self.logger.debug(f"Initialized SDK agent with {len(self.tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SDK agent: {e}")
            raise
    
    async def _setup_message_subscriptions(self):
        """Setup message broker subscriptions"""
        # Subscribe to agent-specific queue
        queue_name = f"{self.agent_role.value}_agent"
        await self.broker.subscribe_queue(queue_name, self._handle_message)
        
        # Subscribe to broadcast channels
        await self.broker.subscribe_channel(MessageType.AGENT_HEALTH_CHECK, self._handle_health_check)
    
    async def _start_message_processing(self):
        """Start processing messages from the queue"""
        queue_name = f"{self.agent_role.value}_agent"
        await self.broker.start_queue_listener(queue_name)
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages with SDK patterns"""
        try:
            self.logger.debug(f"Received message: {message.id} ({message.type.value})")
            
            # Create enhanced context for this message
            context = SDKAgentContext(
                session_id=message.id,
                correlation_id=message.correlation_id,
                metadata=message.payload
            )
            
            # Get or create session for conversation continuity
            session = await self._get_or_create_session(context.session_id)
            context.session = session
            
            self.current_context = context
            self.status = SDKAgentStatus.PROCESSING
            
            # Route message to appropriate handler
            if message.type == MessageType.JOB_CREATED:
                await self._handle_job_request(message, context)
            elif message.type == MessageType.WEBSITE_ANALYZED:
                await self._handle_analysis_result(message, context)
            elif message.type == MessageType.CONTENT_EXTRACTED:
                await self._handle_content_result(message, context)
            else:
                await self._handle_custom_message(message, context)
                
        except Exception as e:
            self.logger.error(f"Error handling message {message.id}: {e}")
            await self._send_error_response(message, str(e))
        finally:
            self.current_context = None
            self.status = SDKAgentStatus.IDLE
    
    async def _get_or_create_session(self, session_id: str) -> Session:
        """Get or create a session for conversation continuity"""
        if session_id not in self.active_sessions:
            # Create new session with timeout
            session = Session(timeout=self.openai_config.session_timeout)
            self.active_sessions[session_id] = session
            self.logger.debug(f"Created new session: {session_id}")
        else:
            session = self.active_sessions[session_id]
            self.logger.debug(f"Using existing session: {session_id}")
        
        return session
    
    async def _handle_job_request(self, message: Message, context: SDKAgentContext):
        """Handle job request - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _handle_job_request")
    
    async def _handle_analysis_result(self, message: Message, context: SDKAgentContext):
        """Handle analysis result - to be implemented by subclasses"""
        pass
    
    async def _handle_content_result(self, message: Message, context: SDKAgentContext):
        """Handle content result - to be implemented by subclasses"""
        pass
    
    async def _handle_custom_message(self, message: Message, context: SDKAgentContext):
        """Handle custom messages - to be implemented by subclasses"""
        pass
    
    async def _handle_health_check(self, message: Message):
        """Handle health check requests"""
        health_status = {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role.value,
            "status": self.status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": len(self.active_sessions),
            "metrics": {
                "jobs_processed": self.metrics.jobs_processed,
                "success_rate": self.metrics.success_rate,
                "average_processing_time": self.metrics.average_processing_time
            }
        }
        
        response = await create_message(
            message_type=MessageType.AGENT_HEALTH_CHECK,
            sender=self.agent_id,
            recipient=message.sender,
            payload=health_status,
            correlation_id=message.correlation_id
        )
        
        await self.broker.publish(response)
    
    async def _register_tools(self):
        """Register available tools - to be implemented by subclasses"""
        pass
    
    def register_function_tool(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Register a function as a tool using SDK patterns"""
        # Use SDK's function_tool decorator
        tool_func = function_tool(func, name=name, description=description)
        self.tools.append(tool_func)
        
        # Store function reference for manual calls if needed
        tool_name = name or func.__name__
        self.tool_functions[tool_name] = func
        
        self.logger.debug(f"Registered function tool: {tool_name}")
    
    def register_handoff_agent(self, agent: Agent):
        """Register another agent for handoffs"""
        self.handoff_agents.append(agent)
        self.logger.debug(f"Registered handoff agent: {agent.name}")
    
    def add_guardrail(self, guardrail: GuardrailFunction):
        """Add a guardrail for input/output validation"""
        self.guardrails.append(guardrail)
        self.logger.debug(f"Added guardrail: {guardrail.__name__}")
    
    async def run_agent(
        self,
        user_message: str,
        context: Optional[SDKAgentContext] = None,
        use_session: bool = True
    ) -> Any:
        """Run the agent with a message using SDK patterns"""
        start_time = time.time()
        
        try:
            if not self.sdk_agent:
                raise RuntimeError("SDK agent not initialized")
            
            # Use existing session or create new one
            if use_session and context and context.session:
                result = await self.runner.run(
                    self.sdk_agent, 
                    user_message, 
                    session=context.session
                )
            else:
                result = await self.runner.run(self.sdk_agent, user_message)
            
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics.total_processing_time += execution_time
            self.metrics.jobs_processed += 1
            
            # Process and return result
            return await self._process_sdk_result(result, execution_time)
            
        except Exception as e:
            self.logger.error(f"Error running agent: {e}")
            self.metrics.error_rate = (self.metrics.error_rate * self.metrics.jobs_processed + 1) / (self.metrics.jobs_processed + 1)
            raise
    
    async def _process_sdk_result(self, result: Any, execution_time: float) -> Dict[str, Any]:
        """Process SDK agent result into standardized format"""
        return {
            "content": getattr(result, 'final_output', str(result)),
            "execution_time": execution_time,
            "session_id": getattr(result, 'session_id', None) if hasattr(result, 'session_id') else None,
            "tool_calls_made": getattr(result, 'tool_calls', []) if hasattr(result, 'tool_calls') else [],
            "handoffs_made": getattr(result, 'handoffs', []) if hasattr(result, 'handoffs') else [],
            "guardrails_triggered": getattr(result, 'guardrails', []) if hasattr(result, 'guardrails') else []
        }
    
    async def create_structured_output_agent(
        self,
        output_schema: Type[BaseModel],
        instructions_suffix: str = ""
    ) -> Agent:
        """Create an agent with structured output using Pydantic models"""
        enhanced_instructions = self.instructions
        if instructions_suffix:
            enhanced_instructions += f"\n\n{instructions_suffix}"
        
        return Agent(
            name=f"{self.agent_id}_structured",
            instructions=enhanced_instructions,
            model=self.model,
            output_type=output_schema,
            tools=self.tools,
            handoffs=self.handoff_agents,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    
    async def _send_response(
        self, 
        message_type: MessageType,
        recipient: str,
        payload: Dict[str, Any],
        correlation_id: str
    ):
        """Send response message"""
        response = await create_message(
            message_type=message_type,
            sender=self.agent_id,
            recipient=recipient,
            payload=payload,
            correlation_id=correlation_id
        )
        
        await self.broker.publish(response)
    
    async def _send_error_response(self, original_message: Message, error: str):
        """Send error response"""
        await self._send_response(
            message_type=MessageType.JOB_FAILED,
            recipient=original_message.sender,
            payload={
                "agent_id": self.agent_id,
                "error": error,
                "original_message_id": original_message.id
            },
            correlation_id=original_message.correlation_id
        )
    
    @asynccontextmanager
    async def agent_session(self, session_id: str):
        """Context manager for agent sessions"""
        session = await self._get_or_create_session(session_id)
        try:
            yield session
        finally:
            # Session cleanup if needed
            pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        if self.metrics.jobs_processed > 0:
            self.metrics.average_processing_time = (
                self.metrics.total_processing_time / self.metrics.jobs_processed
            )
            self.metrics.success_rate = 1.0 - self.metrics.error_rate
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_role.value,
            "status": self.status.value,
            "active_sessions": len(self.active_sessions),
            "jobs_processed": self.metrics.jobs_processed,
            "success_rate": self.metrics.success_rate,
            "average_processing_time": self.metrics.average_processing_time,
            "error_rate": self.metrics.error_rate,
            "total_processing_time": self.metrics.total_processing_time,
            "tools_count": len(self.tools),
            "handoff_agents_count": len(self.handoff_agents),
            "guardrails_count": len(self.guardrails),
            "last_active": datetime.utcnow().isoformat() if self.status != SDKAgentStatus.STOPPED else None
        }


# Helper functions for creating common tool patterns

def create_async_tool(func: Callable) -> Callable:
    """Create an async tool from a function"""
    @function_tool
    async def wrapped_tool(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            return await asyncio.to_thread(func, *args, **kwargs)
    
    wrapped_tool.__name__ = func.__name__
    wrapped_tool.__doc__ = func.__doc__
    return wrapped_tool


def create_validation_guardrail(validation_schema: Type[BaseModel]) -> GuardrailFunction:
    """Create a validation guardrail from a Pydantic schema"""
    def validate_input(ctx, agent, input_data):
        try:
            validation_schema.model_validate(input_data)
            return True, None
        except Exception as e:
            return False, f"Input validation failed: {e}"
    
    return validate_input