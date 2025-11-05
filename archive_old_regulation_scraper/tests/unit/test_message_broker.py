"""
Unit tests for message broker infrastructure
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.message_broker import (
    MessageBroker, 
    Message, 
    MessageType, 
    create_message,
    BrokerManager
)


@pytest.fixture
async def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.lpush.return_value = 1
    redis_mock.brpop.return_value = None
    redis_mock.llen.return_value = 0
    redis_mock.delete.return_value = 1
    redis_mock.publish.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.info.return_value = {
        "used_memory_human": "1MB",
        "connected_clients": 2,
        "uptime_in_seconds": 3600
    }
    return redis_mock


@pytest.fixture
async def broker(mock_redis):
    """Message broker with mocked Redis"""
    broker = MessageBroker("redis://localhost:6379")
    broker.redis_client = mock_redis
    return broker


@pytest.fixture
def sample_message():
    """Sample message for testing"""
    return Message(
        id="test-123",
        type=MessageType.JOB_CREATED,
        sender="test_sender",
        recipient="test_recipient",
        payload={"url": "https://example.com", "job_id": "job-123"},
        correlation_id="corr-123",
        timestamp=datetime.utcnow(),
        ttl=3600
    )


class TestMessage:
    """Test Message class"""
    
    def test_message_creation(self):
        """Test creating a message"""
        msg = Message(
            id="test-1",
            type=MessageType.JOB_CREATED,
            sender="sender",
            recipient="recipient", 
            payload={"test": "data"},
            correlation_id="corr-1",
            timestamp=datetime.utcnow()
        )
        
        assert msg.id == "test-1"
        assert msg.type == MessageType.JOB_CREATED
        assert msg.sender == "sender"
        assert msg.recipient == "recipient"
        assert msg.payload == {"test": "data"}
        assert msg.correlation_id == "corr-1"
        assert isinstance(msg.timestamp, datetime)
    
    def test_message_serialization(self, sample_message):
        """Test message to/from dict conversion"""
        # Convert to dict
        msg_dict = sample_message.to_dict()
        
        assert msg_dict['id'] == "test-123"
        assert msg_dict['type'] == "job_created"
        assert msg_dict['sender'] == "test_sender"
        assert msg_dict['recipient'] == "test_recipient"
        assert msg_dict['payload'] == {"url": "https://example.com", "job_id": "job-123"}
        assert msg_dict['correlation_id'] == "corr-123"
        assert isinstance(msg_dict['timestamp'], str)
        
        # Convert back from dict
        restored_msg = Message.from_dict(msg_dict)
        
        assert restored_msg.id == sample_message.id
        assert restored_msg.type == sample_message.type
        assert restored_msg.sender == sample_message.sender
        assert restored_msg.recipient == sample_message.recipient
        assert restored_msg.payload == sample_message.payload
        assert restored_msg.correlation_id == sample_message.correlation_id
        # Timestamps should be close (within 1 second)
        assert abs((restored_msg.timestamp - sample_message.timestamp).total_seconds()) < 1


class TestMessageBroker:
    """Test MessageBroker class"""
    
    @pytest.mark.asyncio
    async def test_connection(self, mock_redis):
        """Test Redis connection"""
        broker = MessageBroker("redis://localhost:6379")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            await broker.connect()
            
            mock_redis.ping.assert_called_once()
            assert broker.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test Redis connection failure"""
        broker = MessageBroker("redis://localhost:6379")
        
        failing_redis = AsyncMock()
        failing_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('redis.asyncio.from_url', return_value=failing_redis):
            with pytest.raises(Exception, match="Connection failed"):
                await broker.connect()
    
    @pytest.mark.asyncio
    async def test_publish_message(self, broker, sample_message, mock_redis):
        """Test publishing a message"""
        result = await broker.publish(sample_message)
        
        assert result is True
        
        # Verify Redis calls
        mock_redis.lpush.assert_called_once()
        mock_redis.expire.assert_called_once()
        mock_redis.publish.assert_called_once()
        
        # Check the queue name
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == "queue:test_recipient"
        
        # Check message data
        message_data = json.loads(call_args[0][1])
        assert message_data['id'] == "test-123"
        assert message_data['type'] == "job_created"
    
    @pytest.mark.asyncio
    async def test_publish_failure(self, broker, sample_message, mock_redis):
        """Test publish failure handling"""
        mock_redis.lpush.side_effect = Exception("Redis error")
        
        result = await broker.publish(sample_message)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_consume_message(self, broker, sample_message, mock_redis):
        """Test consuming a message from queue"""
        # Mock successful message consumption
        message_json = json.dumps(sample_message.to_dict())
        mock_redis.brpop.return_value = ["queue:test", message_json]
        
        result = await broker.consume_queue("test")
        
        assert result is not None
        assert result.id == sample_message.id
        assert result.type == sample_message.type
        assert result.sender == sample_message.sender
        
        mock_redis.brpop.assert_called_once_with("queue:test", timeout=1)
    
    @pytest.mark.asyncio
    async def test_consume_timeout(self, broker, mock_redis):
        """Test consume timeout"""
        mock_redis.brpop.return_value = None
        
        result = await broker.consume_queue("test", timeout=1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_consume_error(self, broker, mock_redis):
        """Test consume error handling"""
        mock_redis.brpop.side_effect = Exception("Redis error")
        
        result = await broker.consume_queue("test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_queue_size(self, broker, mock_redis):
        """Test getting queue size"""
        mock_redis.llen.return_value = 5
        
        size = await broker.get_queue_size("test")
        assert size == 5
        
        mock_redis.llen.assert_called_once_with("queue:test")
    
    @pytest.mark.asyncio
    async def test_clear_queue(self, broker, mock_redis):
        """Test clearing a queue"""
        mock_redis.llen.return_value = 3
        mock_redis.delete.return_value = 1
        
        cleared = await broker.clear_queue("test")
        assert cleared == 3
        
        mock_redis.llen.assert_called_once_with("queue:test")
        mock_redis.delete.assert_called_once_with("queue:test")
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, broker, mock_redis):
        """Test health check when healthy"""
        health = await broker.health_check()
        
        assert health['status'] == 'healthy'
        assert health['redis'] is True
        assert 'memory_usage' in health
        assert 'connected_clients' in health
        assert 'uptime' in health
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, broker, mock_redis):
        """Test health check when unhealthy"""
        mock_redis.ping.side_effect = Exception("Connection lost")
        
        health = await broker.health_check()
        
        assert health['status'] == 'unhealthy'
        assert health['redis'] is False
        assert 'error' in health
    
    @pytest.mark.asyncio
    async def test_subscribe_queue(self, broker):
        """Test subscribing to a queue"""
        callback = AsyncMock()
        
        await broker.subscribe_queue("test_queue", callback)
        
        assert "queue:test_queue" in broker.subscribers
        assert callback in broker.subscribers["queue:test_queue"]
    
    @pytest.mark.asyncio
    async def test_subscribe_channel(self, broker):
        """Test subscribing to a channel"""
        callback = AsyncMock()
        
        await broker.subscribe_channel(MessageType.JOB_CREATED, callback)
        
        assert "channel:job_created" in broker.subscribers
        assert callback in broker.subscribers["channel:job_created"]
    
    @pytest.mark.asyncio
    async def test_disconnect(self, broker, mock_redis):
        """Test disconnection"""
        await broker.disconnect()
        mock_redis.close.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions"""
    
    @pytest.mark.asyncio
    async def test_create_message(self):
        """Test create_message utility function"""
        message = await create_message(
            message_type=MessageType.JOB_CREATED,
            sender="test_sender",
            recipient="test_recipient",
            payload={"test": "data"},
            correlation_id="corr-123"
        )
        
        assert isinstance(message, Message)
        assert message.type == MessageType.JOB_CREATED
        assert message.sender == "test_sender"
        assert message.recipient == "test_recipient"
        assert message.payload == {"test": "data"}
        assert message.correlation_id == "corr-123"
        assert isinstance(message.timestamp, datetime)
        assert len(message.id) > 0  # UUID should be generated


class TestBrokerManager:
    """Test BrokerManager singleton"""
    
    @pytest.mark.asyncio
    async def test_get_broker_singleton(self):
        """Test broker manager singleton behavior"""
        # Reset singleton
        BrokerManager._instance = None
        
        with patch('src.infrastructure.message_broker.MessageBroker.connect'):
            broker1 = await BrokerManager.get_broker()
            broker2 = await BrokerManager.get_broker()
            
            assert broker1 is broker2
            assert BrokerManager._instance is broker1
    
    @pytest.mark.asyncio
    async def test_close_broker(self):
        """Test closing broker manager"""
        BrokerManager._instance = MagicMock()
        BrokerManager._instance.disconnect = AsyncMock()
        
        await BrokerManager.close_broker()
        
        BrokerManager._instance.disconnect.assert_called_once()
        assert BrokerManager._instance is None