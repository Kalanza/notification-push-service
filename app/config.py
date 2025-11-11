import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/notifications")
    service_name: str = "notification-push-service"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
