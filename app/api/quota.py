"""
Rate limiting API endpoints with standardized response format.
"""

from fastapi import APIRouter, HTTPException
from app.services.rate_limiter import get_user_quota, reset_user_quota, is_rate_limited
from app.logging_config import get_logger
from app.models.response import success_response, error_response

router = APIRouter(prefix="/api/quota", tags=["quota"])
logger = get_logger(__name__)


@router.get("/users/{user_id}")
async def get_quota(user_id: str):
    """Get user's current quota usage (standardized response)"""
    try:
        quota = await get_user_quota(user_id)
        data = {
            "user_id": user_id,
            **quota
        }
        return success_response(
            data=data,
            message=f"Quota retrieved for user {user_id}"
        )
    except Exception as e:
        logger.error(f"Error getting quota for user {user_id}: {e}")
        return error_response(
            error=str(e),
            message="Failed to retrieve quota"
        )


@router.post("/users/{user_id}/reset")
async def reset_quota(user_id: str):
    """Reset user's quota (admin endpoint, standardized response)"""
    try:
        success = await reset_user_quota(user_id)
        if success:
            logger.info(f"Quota reset for user {user_id}")
            return success_response(
                data={"user_id": user_id, "reset": True},
                message=f"Quota reset for user {user_id}"
            )
        else:
            return error_response(
                error="Reset operation failed",
                message="Failed to reset quota"
            )
    except Exception as e:
        logger.error(f"Error resetting quota for user {user_id}: {e}")
        return error_response(
            error=str(e),
            message="Failed to reset quota"
        )


@router.get("/users/{user_id}/check")
async def check_limit(user_id: str):
    """Check if user is rate limited (standardized response)"""
    try:
        is_limited = await is_rate_limited(user_id)
        quota = await get_user_quota(user_id)
        
        data = {
            "user_id": user_id,
            "is_rate_limited": is_limited,
            **quota
        }
        
        message = "User is rate limited" if is_limited else "User is within quota"
        
        return success_response(
            data=data,
            message=message
        )
    except Exception as e:
        logger.error(f"Error checking rate limit for user {user_id}: {e}")
        return error_response(
            error=str(e),
            message="Failed to check rate limit"
        )
