"""
Rate limiting service using Redis token bucket algorithm.
Prevents notification spam per user.
"""

import logging
from typing import Optional
import aioredis
from app.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[aioredis.Redis] = None


async def connect_redis() -> None:
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=True
        )
        logger.info("✅ Connected to Redis for rate limiting")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def disconnect_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def is_rate_limited(
    user_id: str,
    max_notifications: int = 100,
    window_seconds: int = 3600
) -> bool:
    """
    Check if user has exceeded rate limit using token bucket.
    
    Args:
        user_id: User identifier
        max_notifications: Max notifications per window
        window_seconds: Time window in seconds (default: 1 hour)
    
    Returns:
        True if rate limited, False if within limit
    """
    if not redis_client:
        logger.warning("Redis client not initialized, skipping rate limit check")
        return False
    
    try:
        key = f"rate_limit:{user_id}"
        
        # Get current count
        current = await redis_client.get(key)
        
        if current is None:
            # First request in window
            await redis_client.setex(key, window_seconds, 1)
            return False
        
        current_count = int(current)
        
        if current_count >= max_notifications:
            logger.warning(
                f"User {user_id} exceeded rate limit: {current_count}/{max_notifications}"
            )
            return True
        
        # Increment counter
        await redis_client.incr(key)
        return False
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        # Fail open - allow request if Redis fails
        return False


async def get_user_quota(user_id: str, window_seconds: int = 3600) -> dict:
    """
    Get user's current quota usage.
    
    Args:
        user_id: User identifier
        window_seconds: Time window in seconds
    
    Returns:
        Dict with current_count, limit, remaining, reset_in_seconds
    """
    if not redis_client:
        return {
            "current_count": 0,
            "limit": 100,
            "remaining": 100,
            "reset_in_seconds": 0
        }
    
    try:
        key = f"rate_limit:{user_id}"
        current = await redis_client.get(key)
        ttl = await redis_client.ttl(key)
        
        current_count = int(current) if current else 0
        max_limit = 100
        
        return {
            "current_count": current_count,
            "limit": max_limit,
            "remaining": max(0, max_limit - current_count),
            "reset_in_seconds": ttl if ttl > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting quota: {e}")
        return {
            "current_count": 0,
            "limit": 100,
            "remaining": 100,
            "reset_in_seconds": 0
        }


async def reset_user_quota(user_id: str) -> bool:
    """Reset rate limit for user (admin function)"""
    if not redis_client:
        return False
    
    try:
        key = f"rate_limit:{user_id}"
        await redis_client.delete(key)
        logger.info(f"Reset quota for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error resetting quota: {e}")
        return False


async def get_burst_allowance(user_id: str) -> int:
    """
    Calculate burst allowance (temporary increase for peak periods).
    Returns extra tokens available beyond normal limit.
    """
    # Could implement more sophisticated logic here
    # For now, return a fixed burst amount
    return 20
