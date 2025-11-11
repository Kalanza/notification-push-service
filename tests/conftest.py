"""
Pytest fixtures and configuration for push notification service tests.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from aio_pika import IncomingMessage
import asyncpg


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_rabbitmq_channel():
    """Mock RabbitMQ channel"""
    channel = AsyncMock()
    channel.default_exchange = AsyncMock()
    channel.queue = AsyncMock()
    return channel


@pytest_asyncio.fixture
async def mock_redis_client():
    """Mock Redis client"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.incr = AsyncMock(return_value=1)
    client.ping = AsyncMock(return_value=True)
    return client


@pytest_asyncio.fixture
async def mock_postgres_pool():
    """Mock PostgreSQL connection pool"""
    pool = AsyncMock(spec=asyncpg.Pool)
    conn = AsyncMock()
    pool.acquire = AsyncMock(return_value=conn)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return pool


@pytest.fixture
def sample_push_payload():
    """Sample push notification payload"""
    return {
        "notification_id": "notif-123",
        "idempotency_key": "idempotent-123",
        "user_id": "user-456",
        "platform": "android",
        "title": "Test Notification",
        "body": "This is a test notification",
        "device_tokens": ["token1", "token2"],
        "data": {"key": "value"},
        "ttl_seconds": 86400,
        "attempts": 0,
        "meta": {"source": "test"}
    }


@pytest.fixture
def sample_ios_payload():
    """Sample iOS push notification payload"""
    return {
        "notification_id": "notif-ios-123",
        "idempotency_key": "idempotent-ios-123",
        "user_id": "user-789",
        "platform": "ios",
        "title": "iOS Test",
        "body": "Test for iOS",
        "device_tokens": ["ios-token1"],
        "data": {"action": "open_app"},
        "ttl_seconds": 3600,
        "attempts": 0
    }


@pytest.fixture
def sample_web_payload():
    """Sample Web push notification payload"""
    return {
        "notification_id": "notif-web-123",
        "idempotency_key": "idempotent-web-123",
        "user_id": "user-web",
        "platform": "web",
        "title": "Web Notification",
        "body": "Browser notification",
        "device_tokens": ["web-subscription-endpoint"],
        "data": {},
        "ttl_seconds": 3600,  # Fixed: was 604800 (exceeds max 86400)
        "attempts": 0
    }


@pytest_asyncio.fixture
async def mock_incoming_message(sample_push_payload):
    """Mock RabbitMQ incoming message"""
    message = AsyncMock(spec=IncomingMessage)
    message.body = json.dumps(sample_push_payload).encode()
    message.process = AsyncMock()
    message.process.return_value.__aenter__ = AsyncMock()
    message.process.return_value.__aexit__ = AsyncMock(return_value=None)
    message.channel = AsyncMock()
    return message


@pytest.fixture
def mock_firebase_admin():
    """Mock Firebase Admin SDK"""
    with patch('app.services.push_provider.firebase_admin') as mock_fb:
        mock_fb.initialize_app = MagicMock()
        mock_fb.credentials = MagicMock()
        mock_fb.messaging = MagicMock()
        yield mock_fb


@pytest.fixture
def mock_fcm_client():
    """Mock Firebase Cloud Messaging client"""
    client = AsyncMock()
    client.send_multicast = AsyncMock(
        return_value={"success": 2, "failure": 0}
    )
    return client
