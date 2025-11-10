import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    service_name: str = "notification-push-service"

settings = Settings()
