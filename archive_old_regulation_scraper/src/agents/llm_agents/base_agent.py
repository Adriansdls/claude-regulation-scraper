"""
Base LLM Agent
Foundation class for all OpenAI-powered LLM agents in the regulation scraping system
"""
import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import openai
from openai import OpenAI
import tiktoken

from ...infrastructure.message_broker import MessageBroker, Message, MessageType, create_message
from ...config.config_manager import get_config
from ...models.extraction_models import AgentMetrics


class AgentRole(str, Enum):
    """Agent roles in the system"""
    DISCOVERY = "discovery"
    ORCHESTRATOR = "orchestrator" 
    HTML_EXTRACTOR = "html_extractor"
    PDF_ANALYZER = "pdf_analyzer"
    CONTENT_VALIDATOR = "content_validator"
    VISION_PROCESSOR = "vision_processor"


class ToolCallStatus(str, Enum):
    """Status of tool calls"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolResult:
    """Result of a tool execution"""
    tool_name: str
    status: ToolCallStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Context for agent execution"""
    session_id: str
    correlation_id: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)


class BaseLLMAgent:
    """Base class for all OpenAI LLM agents"""
    
    def __init__(
        self, 
        agent_id: str,
        agent_role: AgentRole,
        broker: MessageBroker,
        system_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.broker = broker
        self.system_prompt = system_prompt
        
        # Configuration
        self.config = get_config()
        self.openai_config = self.config.openai
        
        # OpenAI client setup
        self.openai_client = OpenAI(
            api_key=self.openai_config.api_key,
            organization=self.openai_config.organization,
            base_url=self.openai_config.base_url,
            timeout=self.openai_config.timeout,
            max_retries=self.openai_config.max_retries
        )
        
        # Model settings
        self.model = model or self.openai_config.default_model
        self.max_tokens = max_tokens or self.openai_config.max_tokens
        self.temperature = temperature or self.openai_config.temperature
        
        # Token encoding for counting
        self.encoding = tiktoken.encoding_for_model(self.model)
        
        # Tools and capabilities
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        
        # State management
        self.is_running = False
        self.current_context: Optional[AgentContext] = None
        self.metrics = AgentMetrics(
            agent_id=agent_id,
            agent_type=agent_role.value
        )
        
        # Logging
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
    
    async def start(self):
        """Start the LLM agent"""
        if self.is_running:
            self.logger.warning(f"Agent {self.agent_id} is already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting LLM agent: {self.agent_id} ({self.agent_role.value})")
        
        # Subscribe to relevant message queues
        await self._setup_message_subscriptions()
        
        # Initialize tools
        await self._register_tools()
        
        # Start message processing loop
        await self._start_message_processing()
    
    async def stop(self):
        """Stop the LLM agent"""
        self.is_running = False
        self.logger.info(f"Stopping LLM agent: {self.agent_id}")
    
    async def _setup_message_subscriptions(self):
        """Setup message broker subscriptions"""
        # Subscribe to agent-specific queue
        queue_name = f"{self.agent_role.value}_agent"
        await self.broker.subscribe_queue(queue_name, self._handle_message)
        
        # Subscribe to broadcast channels if needed
        await self.broker.subscribe_channel(MessageType.AGENT_HEALTH_CHECK, self._handle_health_check)
    
    async def _start_message_processing(self):
        """Start processing messages from the queue"""
        queue_name = f"{self.agent_role.value}_agent"
        await self.broker.start_queue_listener(queue_name)
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages"""
        try:
            self.logger.debug(f"Received message: {message.id} ({message.type.value})")
            
            # Create context for this message
            context = AgentContext(
                session_id=message.id,
                correlation_id=message.correlation_id,
                metadata=message.payload
            )
            
            self.current_context = context
            
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
    
    async def _handle_job_request(self, message: Message, context: AgentContext):
        """Handle job request - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _handle_job_request")
    
    async def _handle_analysis_result(self, message: Message, context: AgentContext):
        """Handle analysis result - to be implemented by subclasses"""
        pass
    
    async def _handle_content_result(self, message: Message, context: AgentContext):
        """Handle content result - to be implemented by subclasses"""
        pass
    
    async def _handle_custom_message(self, message: Message, context: AgentContext):
        """Handle custom messages - to be implemented by subclasses"""
        pass
    
    async def _handle_health_check(self, message: Message):
        """Handle health check requests"""
        health_status = {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role.value,
            "status": "healthy" if self.is_running else "stopped",
            "timestamp": datetime.utcnow().isoformat(),
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
    
    def register_tool(
        self, 
        name: str, 
        function: Callable, 
        description: str,
        parameters: Dict[str, Any]
    ):
        """Register a tool function"""
        self.tools[name] = function
        
        # Create OpenAI function schema
        tool_schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        
        self.tool_schemas.append(tool_schema)
        self.logger.debug(f"Registered tool: {name}")
    
    async def generate_response(
        self, 
        user_message: str,
        context: Optional[AgentContext] = None,
        use_tools: bool = True
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API"""
        start_time = time.time()
        
        try:
            # Build conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            if context and context.conversation_history:
                messages.extend(context.conversation_history)
            
            messages.append({"role": "user", "content": user_message})
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            
            # Add tools if available and requested
            if use_tools and self.tool_schemas:
                api_params["tools"] = self.tool_schemas
                api_params["tool_choice"] = "auto"
            
            # Count tokens
            input_tokens = self._count_tokens(messages)
            
            self.logger.debug(f"Making OpenAI API call with {input_tokens} input tokens")
            
            # Make API call
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                **api_params
            )
            
            # Process response
            result = await self._process_openai_response(response, context)
            
            # Calculate metrics
            execution_time = time.time() - start_time
            self.metrics.total_processing_time += execution_time
            self.metrics.jobs_processed += 1
            
            result["execution_time"] = execution_time
            result["input_tokens"] = input_tokens
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            self.metrics.error_rate = (self.metrics.error_rate * self.metrics.jobs_processed + 1) / (self.metrics.jobs_processed + 1)
            raise
    
    async def _process_openai_response(
        self, 
        response, 
        context: Optional[AgentContext] = None
    ) -> Dict[str, Any]:
        """Process OpenAI API response"""
        choice = response.choices[0]
        message = choice.message
        
        result = {
            "content": message.content,
            "finish_reason": choice.finish_reason,
            "token_usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "tool_calls": []
        }
        
        # Handle tool calls
        if message.tool_calls:
            tool_results = []
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                self.logger.debug(f"Executing tool: {tool_name}")
                
                tool_result = await self._execute_tool(tool_name, tool_args)
                tool_results.append(tool_result)
                
                if context:
                    context.tool_results.append(tool_result)
            
            result["tool_calls"] = tool_results
        
        return result
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a registered tool"""
        start_time = time.time()
        
        try:
            if tool_name not in self.tools:
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolCallStatus.FAILED,
                    error=f"Tool '{tool_name}' not found"
                )
            
            tool_function = self.tools[tool_name]
            
            # Execute tool function
            if asyncio.iscoroutinefunction(tool_function):
                result = await tool_function(**arguments)
            else:
                result = await asyncio.to_thread(tool_function, **arguments)
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=tool_name,
                status=ToolCallStatus.COMPLETED,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {e}")
            
            return ToolResult(
                tool_name=tool_name,
                status=ToolCallStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages"""
        try:
            text = ""
            for message in messages:
                text += message.get("content", "") + "\n"
            
            return len(self.encoding.encode(text))
            
        except Exception as e:
            self.logger.warning(f"Failed to count tokens: {e}")
            return 0
    
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
            "jobs_processed": self.metrics.jobs_processed,
            "success_rate": self.metrics.success_rate,
            "average_processing_time": self.metrics.average_processing_time,
            "error_rate": self.metrics.error_rate,
            "total_processing_time": self.metrics.total_processing_time,
            "last_active": datetime.utcnow().isoformat() if self.is_running else None
        }