import asyncio
import logging

logger = logging.getLogger(__name__)

async def send_push(payload: dict) -> bool:
    """
    Mock push notification sender.
    In production, integrate FCM / OneSignal here.
    """
    logger.info(f"Sending push notification: {payload}")
    await asyncio.sleep(0.5)  # simulate delay
    return True  # pretend success
