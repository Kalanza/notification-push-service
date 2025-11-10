from fastapi import APIRouter
import aioredis
import aio_pika
from app.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        conn = await aio_pika.connect_robust(settings.rabbitmq_url)
        await conn.close()
        redis = aioredis.from_url(settings.redis_url)
        await redis.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "details": str(e)}
