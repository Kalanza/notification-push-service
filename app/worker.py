import asyncio
import json
import logging
from aio_pika import IncomingMessage
from app.services.rabbitmq import setup_rabbitmq
from app.services.push_provider import send_push

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_message(message: IncomingMessage):
    async with message.process():
        payload = json.loads(message.body)
        logger.info(f"Received message: {payload}")
        success = await send_push(payload)
        if success:
            logger.info("Push sent successfully ✅")
        else:
            logger.error("Push failed ❌")

async def main():
    conn, channel, queue = await setup_rabbitmq()
    await queue.consume(on_message)
    logger.info("Push worker started. Listening for messages...")
    await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
