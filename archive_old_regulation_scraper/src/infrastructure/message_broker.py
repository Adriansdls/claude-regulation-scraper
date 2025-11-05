"""
Message Broker Infrastructure
Provides Redis-based messaging for inter-agent communication
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    """Message types for agent communication"""
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started" 
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    WEBSITE_ANALYZED = "website_analyzed"
    CONTENT_EXTRACTED = "content_extracted"
    CONTENT_VALIDATED = "content_validated"
    VALIDATION_COMPLETED = "validation_completed"
    AGENT_HEALTH_CHECK = "agent_health_check"
    WORKFLOW_REQUEST = "workflow_request"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_COMPLETED = "workflow_completed"


@dataclass
class Message:
    """Standard message structure for agent communication"""
    id: str
    type: MessageType
    sender: str
    recipient: str
    payload: Dict[str, Any]
    correlation_id: str
    timestamp: datetime
    ttl: Optional[int] = 3600  # Message TTL in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = asdict(self)
        data['type'] = self.type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        data['type'] = MessageType(data['type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class MessageBroker:
    """Redis-based message broker for agent communication"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        self.redis_url = redis_url
        self.db = db
        self.redis_client: Optional[redis.Redis] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Establish connection to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Connected to Redis message broker")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Disconnected from Redis message broker")
    
    async def publish(self, message: Message) -> bool:
        """Publish message to specified queue/channel"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
            
        try:
            # Publish to specific recipient queue
            queue_name = f"queue:{message.recipient}"
            message_data = json.dumps(message.to_dict())
            
            # Use list for queue-like behavior
            await self.redis_client.lpush(queue_name, message_data)
            
            # Set TTL on the message
            if message.ttl:
                await self.redis_client.expire(queue_name, message.ttl)
            
            # Also publish to broadcast channel for monitoring
            await self.redis_client.publish(f"channel:{message.type.value}", message_data)
            
            self.logger.debug(f"Published message {message.id} to {message.recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            return False
    
    async def subscribe_queue(self, queue_name: str, callback: Callable[[Message], None]):
        """Subscribe to a specific queue"""
        full_queue_name = f"queue:{queue_name}"
        
        if full_queue_name not in self.subscribers:
            self.subscribers[full_queue_name] = []
        
        self.subscribers[full_queue_name].append(callback)
        self.logger.info(f"Subscribed to queue: {queue_name}")
    
    async def subscribe_channel(self, message_type: MessageType, callback: Callable[[Message], None]):
        """Subscribe to broadcast channel for specific message type"""
        channel_name = f"channel:{message_type.value}"
        
        if channel_name not in self.subscribers:
            self.subscribers[channel_name] = []
            
        self.subscribers[channel_name].append(callback)
        self.logger.info(f"Subscribed to channel: {message_type.value}")
    
    async def consume_queue(self, queue_name: str, timeout: int = 1) -> Optional[Message]:
        """Consume message from queue (blocking pop)"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
            
        try:
            full_queue_name = f"queue:{queue_name}"
            result = await self.redis_client.brpop(full_queue_name, timeout=timeout)
            
            if result:
                _, message_data = result
                message_dict = json.loads(message_data)
                message = Message.from_dict(message_dict)
                
                self.logger.debug(f"Consumed message {message.id} from {queue_name}")
                return message
                
        except asyncio.TimeoutError:
            pass  # Normal timeout, return None
        except Exception as e:
            self.logger.error(f"Failed to consume message: {e}")
            
        return None
    
    async def start_queue_listener(self, queue_name: str):
        """Start listening to queue and process messages"""
        full_queue_name = f"queue:{queue_name}"
        callbacks = self.subscribers.get(full_queue_name, [])
        
        if not callbacks:
            self.logger.warning(f"No subscribers for queue: {queue_name}")
            return
            
        self.logger.info(f"Starting queue listener for: {queue_name}")
        
        while True:
            try:
                message = await self.consume_queue(queue_name, timeout=1)
                if message:
                    # Process message with all registered callbacks
                    for callback in callbacks:
                        try:
                            await callback(message)
                        except Exception as e:
                            self.logger.error(f"Error in callback: {e}")
                            
            except Exception as e:
                self.logger.error(f"Error in queue listener: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def start_channel_listener(self, message_type: MessageType):
        """Start listening to broadcast channel"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
            
        channel_name = f"channel:{message_type.value}"
        callbacks = self.subscribers.get(channel_name, [])
        
        if not callbacks:
            self.logger.warning(f"No subscribers for channel: {message_type.value}")
            return
            
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel_name)
            
            self.logger.info(f"Started channel listener for: {message_type.value}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        message_dict = json.loads(message['data'])
                        msg = Message.from_dict(message_dict)
                        
                        # Process with all callbacks
                        for callback in callbacks:
                            try:
                                await callback(msg)
                            except Exception as e:
                                self.logger.error(f"Error in channel callback: {e}")
                                
                    except Exception as e:
                        self.logger.error(f"Error processing channel message: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error in channel listener: {e}")
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Get number of messages in queue"""
        if not self.redis_client:
            return 0
            
        full_queue_name = f"queue:{queue_name}"
        return await self.redis_client.llen(full_queue_name)
    
    async def clear_queue(self, queue_name: str) -> int:
        """Clear all messages from queue, return number cleared"""
        if not self.redis_client:
            return 0
            
        full_queue_name = f"queue:{queue_name}"
        size = await self.get_queue_size(queue_name)
        await self.redis_client.delete(full_queue_name)
        
        self.logger.info(f"Cleared {size} messages from queue: {queue_name}")
        return size
    
    async def health_check(self) -> Dict[str, Any]:
        """Check broker health status"""
        if not self.redis_client:
            return {"status": "disconnected", "redis": False}
            
        try:
            await self.redis_client.ping()
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "redis": True,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "redis": False, "error": str(e)}


# Utility functions for common messaging patterns
async def create_message(
    message_type: MessageType,
    sender: str,
    recipient: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    ttl: Optional[int] = 3600
) -> Message:
    """Create a new message with generated ID and timestamp"""
    import uuid
    
    # Generate correlation_id if not provided
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    return Message(
        id=str(uuid.uuid4()),
        type=message_type,
        sender=sender,
        recipient=recipient,
        payload=payload,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow(),
        ttl=ttl
    )


class BrokerManager:
    """Singleton manager for message broker instance"""
    _instance: Optional[MessageBroker] = None
    
    @classmethod
    async def get_broker(cls, redis_url: str = "redis://localhost:6379") -> MessageBroker:
        """Get or create broker instance"""
        if cls._instance is None:
            cls._instance = MessageBroker(redis_url)
            await cls._instance.connect()
        return cls._instance
    
    @classmethod
    async def close_broker(cls):
        """Close broker connection"""
        if cls._instance:
            await cls._instance.disconnect()
            cls._instance = None