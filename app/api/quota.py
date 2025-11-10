"""
Rate limiting API endpoints.
"""

from fastapi import APIRouter, HTTPException
from app.services.rate_limiter import get_user_quota, reset_user_quota, is_rate_limited
from app.logging_config import get_logger

router = APIRouter(prefix="/api/quota", tags=["quota"])
logger = get_logger(__name__)


@router.get("/users/{user_id}")
async def get_quota(user_id: str):
    """Get user's current quota usage"""
    quota = await get_user_quota(user_id)
    return {
        "user_id": user_id,
        **quota
    }


@router.post("/users/{user_id}/reset")
async def reset_quota(user_id: str):
    """Reset user's quota (admin endpoint)"""
    success = await reset_user_quota(user_id)
    if success:
        logger.info(f"Quota reset for user {user_id}")
        return {"message": f"Quota reset for user {user_id}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset quota")


@router.get("/users/{user_id}/check")
async def check_limit(user_id: str):
    """Check if user is rate limited"""
    is_limited = await is_rate_limited(user_id)
    quota = await get_user_quota(user_id)
    
    return {
        "user_id": user_id,
        "is_rate_limited": is_limited,
        **quota
    }
