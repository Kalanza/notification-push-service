from redis import asyncio as aioredis
from app.config import settings

redis = aioredis.from_url(settings.redis_url, decode_responses=True)

async def is_processed(key: str) -> bool:
    if not key:
        return False
    return await redis.exists(f"processed:{key}")

async def mark_processed(key: str, ttl: int = 86400):
    if key:
        await redis.set(f"processed:{key}", "1", ex=ttl)
