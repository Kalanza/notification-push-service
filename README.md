# Notification Push Service

Push notification microservice for Android, iOS, and Web platforms using Firebase Cloud Messaging.

## Features

- Multi-platform push notifications (Android, iOS, Web)
- Circuit breaker pattern for fault tolerance
- Retry logic with exponential backoff
- Idempotency (24-hour TTL)
- Rate limiting (100 notifications/hour/user)
- PostgreSQL persistence with audit logging
- Structured JSON logging with correlation IDs

## Quick Start

**Start services:**
```bash
docker-compose up -d
```

**Check health:**
```bash
curl http://localhost:8080/health
```

**Run tests:**
```bash
pytest tests/ -v
```

## API Endpoints

- `GET /health` - Service health check
- `GET /api/quota/users/{user_id}` - Get user quota
- `GET /api/quota/users/{user_id}/check` - Check rate limit
- `POST /api/quota/users/{user_id}/reset` - Reset quota

## Configuration

Set environment variables:
```bash
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/notifications
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json
```

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Language:** Python 3.11
- **Queue:** RabbitMQ
- **Cache:** Redis
- **Database:** PostgreSQL
- **Push Provider:** Firebase Cloud Messaging
