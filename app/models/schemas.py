from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


class PushNotificationSchema(BaseModel):
    """
    Complete push notification message schema.
    Validates incoming messages from RabbitMQ.
    """
    
    # Required fields
    idempotency_key: str = Field(..., description="UUID for idempotency deduplication")
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique notification ID")
    user_id: str = Field(..., description="Target user ID")
    platform: str = Field(..., description="Target platform: android|ios|web")
    title: str = Field(..., min_length=1, max_length=100, description="Notification title")
    body: str = Field(..., min_length=1, max_length=500, description="Notification body/content")
    
    # Device tokens (either user_id or device_tokens must be provided)
    device_tokens: Optional[List[str]] = Field(default=None, description="Target device tokens (optional if user_id provided)")
    
    # Optional fields
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional data payload")
    ttl_seconds: int = Field(default=3600, ge=0, le=86400, description="Time-to-live for notification (seconds)")
    
    # Internal tracking
    attempts: int = Field(default=0, ge=0, description="Retry attempt counter")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata for tracking")
    
    class Config:
        schema_extra = {
            "example": {
                "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
                "notification_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "user-123",
                "platform": "android",
                "title": "Welcome!",
                "body": "Hello, thanks for joining our app!",
                "device_tokens": ["device-token-1", "device-token-2"],
                "data": {
                    "click_action": "OPEN_APP",
                    "url": "https://example.com/promo"
                },
                "ttl_seconds": 3600,
                "attempts": 0,
                "meta": {
                    "campaign_id": "summer-2025",
                    "segment": "new_users"
                }
            }
        }
    
    @validator("platform")
    def validate_platform(cls, v):
        """Validate platform is one of: android, ios, web"""
        allowed = {"android", "ios", "web"}
        if v.lower() not in allowed:
            raise ValueError(f"Platform must be one of {allowed}")
        return v.lower()
    
    @validator("idempotency_key")
    def validate_idempotency_key(cls, v):
        """Ensure idempotency_key is not empty"""
        if not v or not v.strip():
            raise ValueError("idempotency_key cannot be empty")
        return v.strip()
    
    @validator("device_tokens", always=True)
    def validate_tokens(cls, v, values):
        """Ensure we have either device_tokens or will resolve from user_id"""
        # If device_tokens is empty list, convert to None
        if v is not None and not isinstance(v, list):
            raise ValueError("device_tokens must be a list")
        if v is not None and len(v) == 0:
            return None
        return v


class PushNotificationResponse(BaseModel):
    """Response after processing a push notification"""
    status: str = Field(..., description="Processing status: queued|sent|failed")
    notification_id: str = Field(..., description="Notification ID")
    message: str = Field(default="", description="Status message")
    retry_after: Optional[int] = Field(default=None, description="Seconds to retry if failed")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "queued",
                "notification_id": "550e8400-e29b-41d4-a716-446655440001",
                "message": "Notification queued for processing"
            }
        }


class NotificationStatus(BaseModel):
    """Track notification delivery status"""
    notification_id: str
    user_id: str
    platform: str
    status: str  # pending, sent, failed, delivered, read
    created_at: str
    updated_at: str
    provider_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    attempts: int = 0
