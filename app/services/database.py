"""
PostgreSQL database service for notification persistence.
Handles connection pooling and notification status tracking.
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """Async PostgreSQL connection pool manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                ssl='prefer'
            )
            logger.info("✅ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
    
    async def execute(self, query: str, *args) -> Any:
        """Execute a query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[dict]:
        """Fetch rows from query"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetchone(self, query: str, *args) -> Optional[dict]:
        """Fetch single row from query"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None


# Global pool instance
db_pool = DatabasePool()


async def init_db() -> None:
    """Initialize database tables"""
    await db_pool.connect()
    
    async with db_pool.pool.acquire() as conn:
        # Create notifications table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                notification_id VARCHAR(36) UNIQUE NOT NULL,
                idempotency_key VARCHAR(36) UNIQUE NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                platform VARCHAR(20) NOT NULL,
                title VARCHAR(255) NOT NULL,
                body TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                device_tokens TEXT[],
                attempts INT DEFAULT 0,
                provider_response JSONB,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes for notifications table
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON notifications(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON notifications(status)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON notifications(created_at)
        """)
        
        # Create notification_logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id SERIAL PRIMARY KEY,
                notification_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                event VARCHAR(50),
                message TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes for notification_logs table
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_notification_id ON notification_logs(notification_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_event ON notification_logs(event)
        """)
        
        logger.info("✅ Database tables initialized")


async def save_notification(
    notification_id: str,
    idempotency_key: str,
    user_id: str,
    platform: str,
    title: str,
    body: str,
    device_tokens: List[str],
    status: str = "pending"
) -> bool:
    """Save notification to database"""
    try:
        query = """
            INSERT INTO notifications 
            (notification_id, idempotency_key, user_id, platform, title, body, status, device_tokens)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (notification_id) DO UPDATE SET updated_at = NOW()
        """
        await db_pool.execute(
            query,
            notification_id,
            idempotency_key,
            user_id,
            platform,
            title,
            body,
            status,
            device_tokens
        )
        logger.info(f"✅ Saved notification {notification_id} to database")
        return True
    except Exception as e:
        logger.error(f"Error saving notification: {e}")
        return False


async def update_notification_status(
    notification_id: str,
    status: str,
    attempts: int = 0,
    provider_response: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> bool:
    """Update notification status"""
    try:
        query = """
            UPDATE notifications
            SET status = $1, attempts = $2, provider_response = $3, 
                error_message = $4, updated_at = NOW()
            WHERE notification_id = $5
        """
        await db_pool.execute(
            query,
            status,
            attempts,
            provider_response,
            error_message,
            notification_id
        )
        logger.info(f"✅ Updated notification {notification_id} status to {status}")
        return True
    except Exception as e:
        logger.error(f"Error updating notification status: {e}")
        return False


async def log_notification_event(
    notification_id: str,
    user_id: str,
    event: str,
    message: str = ""
) -> bool:
    """Log notification event for audit trail"""
    try:
        query = """
            INSERT INTO notification_logs (notification_id, user_id, event, message)
            VALUES ($1, $2, $3, $4)
        """
        await db_pool.execute(query, notification_id, user_id, event, message)
        return True
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        return False


async def get_notification(notification_id: str) -> Optional[Dict[str, Any]]:
    """Get notification details"""
    try:
        query = "SELECT * FROM notifications WHERE notification_id = $1"
        return await db_pool.fetchone(query, notification_id)
    except Exception as e:
        logger.error(f"Error fetching notification: {e}")
        return None


async def get_notifications_by_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get user notifications with pagination"""
    try:
        query = """
            SELECT * FROM notifications 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2
        """
        return await db_pool.fetch(query, user_id, limit)
    except Exception as e:
        logger.error(f"Error fetching user notifications: {e}")
        return []


async def get_failed_notifications(limit: int = 50) -> List[Dict[str, Any]]:
    """Get failed notifications for retry/investigation"""
    try:
        query = """
            SELECT * FROM notifications 
            WHERE status = 'failed' 
            ORDER BY updated_at ASC 
            LIMIT $1
        """
        return await db_pool.fetch(query, limit)
    except Exception as e:
        logger.error(f"Error fetching failed notifications: {e}")
        return []
