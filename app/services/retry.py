import asyncio
import json
import logging
from aio_pika import Message

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _calculate_delay(attempts: int) -> int:
    """Calculate exponential backoff delay (2^attempts)"""
    return 2 ** attempts


async def retry_message(channel, message, payload):
    attempts = payload.get("attempts", 0) + 1
    payload["attempts"] = attempts

    if attempts >= MAX_RETRIES:
        logger.warning("Max retries reached, sending to DLQ")
        await channel.default_exchange.publish(
            Message(json.dumps(payload).encode()), routing_key="failed"
        )
        return

    delay = _calculate_delay(attempts)  # Use the function
    logger.info(f"Retrying in {delay}s (attempt {attempts})")
    await asyncio.sleep(delay)

    await channel.default_exchange.publish(
        Message(json.dumps(payload).encode()), routing_key="push"
    )
