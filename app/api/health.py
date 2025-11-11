from fastapi import APIRouter, status
import aio_pika
from redis import asyncio as aioredis
from app.config import settings
from app.services.database import db_pool
from app.logging_config import get_logger
from app.models.response import success_response, error_response

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """
    Comprehensive health check for all service dependencies.
    Returns status for RabbitMQ, Redis, and PostgreSQL in standardized format.
    """
    health_data = {
        "service": "notification-push-service",
        "rabbitmq": "unknown",
        "redis": "unknown",
        "database": "unknown"
    }
    
    all_healthy = True
    
    # Check RabbitMQ
    try:
        conn = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=5)
        await conn.close()
        health_data["rabbitmq"] = "connected"
        logger.debug("RabbitMQ health check: OK")
    except Exception as e:
        health_data["rabbitmq"] = f"disconnected: {str(e)}"
        all_healthy = False
        logger.error(f"RabbitMQ health check failed: {e}")
    
    # Check Redis
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        await redis.close()
        health_data["redis"] = "connected"
        logger.debug("Redis health check: OK")
    except Exception as e:
        health_data["redis"] = f"disconnected: {str(e)}"
        all_healthy = False
        logger.error(f"Redis health check failed: {e}")
    
    # Check PostgreSQL
    try:
        if db_pool.pool is None:
            health_data["database"] = "disconnected: pool not initialized"
            all_healthy = False
        else:
            async with db_pool.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_data["database"] = "connected"
            logger.debug("PostgreSQL health check: OK")
    except Exception as e:
        health_data["database"] = f"disconnected: {str(e)}"
        all_healthy = False
        logger.error(f"PostgreSQL health check failed: {e}")
    
    # Return standardized response
    if all_healthy:
        return success_response(
            data=health_data,
            message="All services healthy"
        )
    else:
        return error_response(
            error="One or more services unavailable",
            message="Service health check degraded",
            data=health_data
        )

