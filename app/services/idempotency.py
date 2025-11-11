from redis import asyncio as aioredis
from app.config import settings

# Global redis client for mocking in tests
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
redis = redis_client  # Alias for backward compatibility

async def is_processed(key: str) -> bool:
    if not key:
        return False
    return await redis_client.exists(f"processed:{key}")

async def mark_processed(key: str, ttl: int = 86400):
    if key:
        await redis_client.set(f"processed:{key}", "1", ex=ttl)
