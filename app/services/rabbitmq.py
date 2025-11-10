from aio_pika import connect_robust, ExchangeType
from app.config import settings

async def setup_rabbitmq():
    connection = await connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange("notifications.direct", ExchangeType.DIRECT)
    queue = await channel.declare_queue("push.queue", durable=True)
    await queue.bind(exchange, routing_key="push")
    return connection, channel, queue
