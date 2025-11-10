import asyncio
import json
import logging
from aio_pika import IncomingMessage
from app.services.rabbitmq import setup_rabbitmq
from app.services.push_provider import send_push
from app.services.idempotency import is_processed, mark_processed
from app.services.retry import retry_message
from app.services.circuit_breaker import CircuitBreaker
from app.services.database import save_notification, update_notification_status, log_notification_event

logger = logging.getLogger(__name__)
breaker = CircuitBreaker()


async def on_message(message: IncomingMessage):
    async with message.process(ignore_processed=True):
        payload = json.loads(message.body)
        key = payload.get("idempotency_key")
        notification_id = payload.get("notification_id")
        user_id = payload.get("user_id")
        
        if await is_processed(key):
            logger.info(f"📋 Duplicate message skipped for {notification_id}")
            return

        # Save notification to database
        await save_notification(
            notification_id=notification_id,
            idempotency_key=key,
            user_id=user_id,
            platform=payload.get("platform"),
            title=payload.get("title"),
            body=payload.get("body"),
            device_tokens=payload.get("device_tokens", []),
            status="processing"
        )
        
        await log_notification_event(
            notification_id=notification_id,
            user_id=user_id,
            event="received",
            message="Notification received from queue"
        )

        try:
            success = await breaker.call(send_push, payload)
            if success:
                await mark_processed(key)
                await update_notification_status(
                    notification_id=notification_id,
                    status="sent",
                    attempts=payload.get("attempts", 0)
                )
                await log_notification_event(
                    notification_id=notification_id,
                    user_id=user_id,
                    event="sent",
                    message="Push notification sent successfully"
                )
                logger.info(f"✅ Push sent successfully for {notification_id}")
            else:
                raise Exception("Send failed")
        except Exception as e:
            logger.warning(f"⚠️ Error sending {notification_id}: {e}. Retrying...")
            await log_notification_event(
                notification_id=notification_id,
                user_id=user_id,
                event="retry",
                message=f"Retry attempt due to: {str(e)}"
            )
            channel = message.channel
            await retry_message(channel, message, payload)
