"""
Queue Manager
Handles queue creation, management, and routing logic for the regulation scraping system
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from .message_broker import MessageBroker, Message, MessageType


class QueuePriority(Enum):
    """Queue priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class QueueType(Enum):
    """Types of queues in the system"""
    DISCOVERY = "discovery"
    HTML_EXTRACTION = "html_extraction"
    PDF_EXTRACTION = "pdf_extraction"
    VISION_EXTRACTION = "vision_extraction"
    CONTENT_ANALYSIS = "content_analysis"
    VALIDATION = "validation"
    ORCHESTRATOR = "orchestrator"
    DEAD_LETTER = "dead_letter"


@dataclass
class QueueConfig:
    """Configuration for a queue"""
    name: str
    queue_type: QueueType
    priority: QueuePriority
    max_size: int = 1000
    consumer_timeout: int = 30
    max_retries: int = 3
    ttl_seconds: int = 3600
    enable_dead_letter: bool = True


class QueueManager:
    """Manages all queues in the regulation scraping system"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.logger = logging.getLogger(__name__)
        self.queues: Dict[str, QueueConfig] = {}
        self.queue_stats: Dict[str, Dict] = {}
        self._setup_default_queues()
    
    def _setup_default_queues(self):
        """Setup default queues for the system"""
        default_configs = [
            QueueConfig(
                name="orchestrator",
                queue_type=QueueType.ORCHESTRATOR,
                priority=QueuePriority.CRITICAL,
                max_size=500
            ),
            QueueConfig(
                name="discovery",
                queue_type=QueueType.DISCOVERY,
                priority=QueuePriority.HIGH,
                max_size=200
            ),
            QueueConfig(
                name="html_extraction",
                queue_type=QueueType.HTML_EXTRACTION,
                priority=QueuePriority.NORMAL,
                max_size=1000
            ),
            QueueConfig(
                name="pdf_extraction", 
                queue_type=QueueType.PDF_EXTRACTION,
                priority=QueuePriority.NORMAL,
                max_size=500
            ),
            QueueConfig(
                name="vision_extraction",
                queue_type=QueueType.VISION_EXTRACTION,
                priority=QueuePriority.LOW,  # Resource intensive
                max_size=100
            ),
            QueueConfig(
                name="content_analysis",
                queue_type=QueueType.CONTENT_ANALYSIS,
                priority=QueuePriority.NORMAL,
                max_size=500
            ),
            QueueConfig(
                name="validation",
                queue_type=QueueType.VALIDATION,
                priority=QueuePriority.HIGH,
                max_size=500
            ),
            QueueConfig(
                name="dead_letter",
                queue_type=QueueType.DEAD_LETTER,
                priority=QueuePriority.LOW,
                max_size=1000,
                enable_dead_letter=False  # Dead letter queue doesn't need its own DLQ
            )
        ]
        
        for config in default_configs:
            self.register_queue(config)
    
    def register_queue(self, config: QueueConfig):
        """Register a new queue configuration"""
        self.queues[config.name] = config
        self.queue_stats[config.name] = {
            "created_at": datetime.utcnow(),
            "total_messages": 0,
            "failed_messages": 0,
            "successful_messages": 0,
            "last_activity": None
        }
        self.logger.info(f"Registered queue: {config.name} ({config.queue_type.value})")
    
    async def create_queues(self):
        """Create all registered queues in Redis"""
        for queue_name, config in self.queues.items():
            try:
                # Initialize queue stats in Redis
                queue_key = f"queue_stats:{queue_name}"
                stats = {
                    "config": {
                        "type": config.queue_type.value,
                        "priority": config.priority.value,
                        "max_size": config.max_size,
                        "ttl_seconds": config.ttl_seconds
                    },
                    "stats": self.queue_stats[queue_name]
                }
                
                await self.broker.redis_client.hset(
                    queue_key,
                    mapping={"data": str(stats)}
                )
                
                self.logger.debug(f"Created queue metadata for: {queue_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to create queue {queue_name}: {e}")
    
    async def route_message(self, message: Message) -> bool:
        """Route message to appropriate queue based on type and content"""
        try:
            # Determine target queue based on message type
            target_queue = self._get_target_queue(message)
            
            if not target_queue:
                self.logger.error(f"No target queue found for message type: {message.type}")
                await self._send_to_dead_letter(message, "No target queue")
                return False
            
            # Check queue capacity
            if await self._is_queue_full(target_queue):
                self.logger.warning(f"Queue {target_queue} is full, routing to dead letter")
                await self._send_to_dead_letter(message, "Queue full")
                return False
            
            # Update message recipient to target queue
            message.recipient = target_queue
            
            # Send message
            success = await self.broker.publish(message)
            
            if success:
                await self._update_queue_stats(target_queue, "sent")
                self.logger.debug(f"Routed message {message.id} to {target_queue}")
            else:
                await self._send_to_dead_letter(message, "Send failed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error routing message: {e}")
            await self._send_to_dead_letter(message, f"Routing error: {e}")
            return False
    
    def _get_target_queue(self, message: Message) -> Optional[str]:
        """Determine target queue based on message type"""
        routing_map = {
            MessageType.JOB_CREATED: "orchestrator",
            MessageType.JOB_STARTED: "orchestrator",
            MessageType.JOB_COMPLETED: "orchestrator",
            MessageType.JOB_FAILED: "orchestrator",
            MessageType.WEBSITE_ANALYZED: "html_extraction",  # Default next step
            MessageType.CONTENT_EXTRACTED: "validation",
            MessageType.VALIDATION_COMPLETED: "orchestrator"
        }
        
        # Check if recipient is explicitly set
        if message.recipient and message.recipient in self.queues:
            return message.recipient
            
        # Use routing map
        return routing_map.get(message.type)
    
    async def _is_queue_full(self, queue_name: str) -> bool:
        """Check if queue has reached capacity"""
        config = self.queues.get(queue_name)
        if not config:
            return True
            
        current_size = await self.broker.get_queue_size(queue_name)
        return current_size >= config.max_size
    
    async def _send_to_dead_letter(self, message: Message, reason: str):
        """Send message to dead letter queue"""
        try:
            # Add failure reason to payload
            dead_letter_payload = {
                "original_message": message.to_dict(),
                "failure_reason": reason,
                "failed_at": datetime.utcnow().isoformat(),
                "original_recipient": message.recipient
            }
            
            # Create dead letter message
            dead_letter_msg = Message(
                id=f"dl_{message.id}",
                type=MessageType.JOB_FAILED,
                sender="queue_manager",
                recipient="dead_letter",
                payload=dead_letter_payload,
                correlation_id=message.correlation_id,
                timestamp=datetime.utcnow(),
                ttl=86400  # Keep dead letters for 24 hours
            )
            
            await self.broker.publish(dead_letter_msg)
            await self._update_queue_stats(message.recipient or "unknown", "failed")
            
            self.logger.warning(f"Sent message {message.id} to dead letter: {reason}")
            
        except Exception as e:
            self.logger.error(f"Failed to send to dead letter: {e}")
    
    async def _update_queue_stats(self, queue_name: str, action: str):
        """Update queue statistics"""
        try:
            if queue_name in self.queue_stats:
                stats = self.queue_stats[queue_name]
                stats["last_activity"] = datetime.utcnow()
                
                if action == "sent":
                    stats["total_messages"] += 1
                elif action == "success":
                    stats["successful_messages"] += 1
                elif action == "failed":
                    stats["failed_messages"] += 1
                
                # Update in Redis
                queue_key = f"queue_stats:{queue_name}"
                await self.broker.redis_client.hset(
                    queue_key,
                    "last_updated",
                    datetime.utcnow().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update queue stats: {e}")
    
    async def get_queue_info(self, queue_name: str) -> Optional[Dict]:
        """Get detailed information about a queue"""
        if queue_name not in self.queues:
            return None
            
        try:
            config = self.queues[queue_name]
            current_size = await self.broker.get_queue_size(queue_name)
            stats = self.queue_stats[queue_name].copy()
            
            return {
                "name": queue_name,
                "type": config.queue_type.value,
                "priority": config.priority.value,
                "current_size": current_size,
                "max_size": config.max_size,
                "utilization": (current_size / config.max_size) * 100,
                "config": {
                    "consumer_timeout": config.consumer_timeout,
                    "max_retries": config.max_retries,
                    "ttl_seconds": config.ttl_seconds,
                    "enable_dead_letter": config.enable_dead_letter
                },
                "stats": stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get queue info: {e}")
            return None
    
    async def get_all_queues_status(self) -> Dict[str, Dict]:
        """Get status of all queues"""
        status = {}
        
        for queue_name in self.queues.keys():
            queue_info = await self.get_queue_info(queue_name)
            if queue_info:
                status[queue_name] = queue_info
                
        return status
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue"""
        if queue_name not in self.queues:
            self.logger.error(f"Queue {queue_name} not found")
            return 0
            
        try:
            cleared_count = await self.broker.clear_queue(queue_name)
            await self._update_queue_stats(queue_name, "purged")
            
            self.logger.info(f"Purged {cleared_count} messages from {queue_name}")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to purge queue {queue_name}: {e}")
            return 0
    
    async def requeue_dead_letters(self, limit: int = 100) -> int:
        """Requeue messages from dead letter queue"""
        requeued = 0
        
        try:
            for _ in range(limit):
                message = await self.broker.consume_queue("dead_letter", timeout=1)
                if not message:
                    break
                    
                # Extract original message from dead letter payload
                original_data = message.payload.get("original_message")
                if not original_data:
                    continue
                    
                original_message = Message.from_dict(original_data)
                
                # Attempt to route again
                if await self.route_message(original_message):
                    requeued += 1
                    self.logger.info(f"Requeued dead letter message: {original_message.id}")
                else:
                    # Put back in dead letter if still failing
                    await self.broker.publish(message)
                    break
                    
        except Exception as e:
            self.logger.error(f"Error requeuing dead letters: {e}")
            
        return requeued
    
    async def monitor_queues(self, alert_threshold: float = 0.8):
        """Monitor queue health and send alerts if needed"""
        try:
            status = await self.get_all_queues_status()
            alerts = []
            
            for queue_name, info in status.items():
                utilization = info.get("utilization", 0) / 100
                
                if utilization >= alert_threshold:
                    alerts.append({
                        "queue": queue_name,
                        "utilization": utilization,
                        "current_size": info.get("current_size", 0),
                        "max_size": info.get("max_size", 0)
                    })
            
            if alerts:
                self.logger.warning(f"Queue alerts: {alerts}")
                # Here you could send alerts to monitoring system
                
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring queues: {e}")
            return []