import asyncio
import logging
from typing import Dict, List, Any
from firebase_admin import messaging
import firebase_admin
from app.services.rate_limiter import is_rate_limited

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (will use GOOGLE_APPLICATION_CREDENTIALS env var)
try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    fcm_client = messaging.Client()
    FIREBASE_INITIALIZED = True
except Exception as e:
    logger.warning(f"Firebase not initialized: {e}. Using mock mode.")
    FIREBASE_INITIALIZED = False


async def send_push(payload: dict) -> bool:
    """
    Send push notification via Firebase Cloud Messaging (FCM).
    Falls back to mock mode if FCM not configured.
    Respects per-user rate limiting.
    
    Args:
        payload: Notification payload with title, body, device_tokens, data
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        user_id = payload.get("user_id", "unknown")
        platform = payload.get("platform", "android").lower()
        device_tokens = payload.get("device_tokens", [])
        notification_id = payload.get("notification_id", "unknown")
        
        # Check rate limit
        if await is_rate_limited(user_id):
            logger.warning(f"User {user_id} exceeded rate limit for notification {notification_id}")
            return False
        
        if not device_tokens:
            logger.warning(f"No device tokens provided for notification {notification_id}")
            return False
        
        # Build notification
        title = payload.get("title", "Notification")
        body = payload.get("body", "")
        data = payload.get("data", {})
        
        # Add correlation IDs to data
        data["notification_id"] = notification_id
        data["idempotency_key"] = payload.get("idempotency_key", "")
        
        if FIREBASE_INITIALIZED:
            return await _send_via_fcm(
                device_tokens, 
                title, 
                body, 
                data, 
                platform, 
                notification_id,
                ttl_seconds=payload.get("ttl_seconds", 3600)
            )
        else:
            return await _send_mock(device_tokens, title, body, data, notification_id)
            
    except Exception as e:
        logger.error(f"Error sending push: {e}", exc_info=True)
        return False


async def _send_via_fcm(
    device_tokens: List[str],
    title: str,
    body: str,
    data: Dict[str, Any],
    platform: str,
    notification_id: str,
    ttl_seconds: int = 3600
) -> bool:
    """
    Send via Firebase Cloud Messaging.
    Handles batch sending and multi-platform support.
    """
    try:
        # Send to multiple tokens (FCM can handle up to 500 at once)
        successful_count = 0
        failed_tokens = []
        
        for token in device_tokens:
            try:
                # Build platform-specific message
                message = messaging.MulticastMessage(
                    tokens=[token],
                    notification=messaging.Notification(title=title, body=body),
                    data=data,
                    android=messaging.AndroidConfig(
                        ttl=ttl_seconds,
                        priority="high"
                    ) if platform in ["android", "hybrid"] else None,
                    apns=messaging.APNSConfig(
                        headers={"apns-priority": "10"}
                    ) if platform in ["ios", "hybrid"] else None,
                    webpush=messaging.WebpushConfig(
                        headers={"TTL": str(ttl_seconds)}
                    ) if platform in ["web", "hybrid"] else None
                )
                
                response = fcm_client.send_multicast(message)
                
                if response.success_count > 0:
                    successful_count += 1
                    logger.info(f"✅ Sent notification {notification_id} to token {token[:20]}...")
                
                if response.failure_count > 0:
                    failed_tokens.append(token)
                    logger.warning(f"⚠️ Failed to send to token {token[:20]}... for notification {notification_id}")
                    
            except Exception as e:
                failed_tokens.append(token)
                logger.error(f"Error sending to token {token[:20]}...: {e}")
        
        # Log results
        logger.info(
            f"Notification {notification_id}: {successful_count}/{len(device_tokens)} sent",
            extra={
                "notification_id": notification_id,
                "platform": platform,
                "successful": successful_count,
                "failed": len(failed_tokens)
            }
        )
        
        return successful_count > 0
        
    except Exception as e:
        logger.error(f"FCM send error for notification {notification_id}: {e}", exc_info=True)
        return False


async def _send_mock(
    device_tokens: List[str],
    title: str,
    body: str,
    data: Dict[str, Any],
    notification_id: str
) -> bool:
    """
    Mock push notification sender (for development/testing).
    Simulates successful send without actual FCM.
    """
    logger.info(
        f"[MOCK MODE] Sending notification {notification_id}",
        extra={
            "notification_id": notification_id,
            "title": title,
            "body": body,
            "device_tokens_count": len(device_tokens),
            "data": data
        }
    )
    await asyncio.sleep(0.1)  # Simulate network delay
    return True
