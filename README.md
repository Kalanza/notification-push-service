# 📬 Notification Push Service

A production-ready FastAPI microservice for sending push notifications across multiple platforms (Android, iOS, Web) with enterprise-grade reliability, resilience patterns, and observability.

## ✨ Features

- **Multi-Platform Support**: Send notifications to Android, iOS, and Web devices
- **Firebase Cloud Messaging**: Integrated FCM with fallback to mock mode for development
- **Message Validation**: Comprehensive Pydantic schemas with automatic validation
- **Idempotency**: Redis-backed deduplication to prevent duplicate processing (24h TTL)
- **Resilience**: Circuit breaker pattern to handle provider failures gracefully
- **Retry Logic**: Exponential backoff with max 3 attempts and dead letter queue
- **Rate Limiting**: Per-user token bucket algorithm (100 notifications/hour)
- **Database Persistence**: PostgreSQL with full audit trail logging
- **Structured Logging**: JSON logs with correlation IDs for complete traceability
- **Health Checks**: Connectivity verification for RabbitMQ, Redis, and PostgreSQL
- **Docker Ready**: Complete Docker and Docker Compose setup for local development

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

### Local Development

1. **Clone and install**
```bash
git clone <repository>
cd notification-push-service
pip install -r requirements.txt
```

2. **Start all services**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL 15 (port 5432)
- RabbitMQ 3 (port 5672, management UI on 15672)
- Redis 7 (port 6379)
- Push Service API (port 8080)

3. **Verify health**
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "rabbitmq": "connected",
  "redis": "connected",
  "database": "connected"
}
```

4. **Run tests**
```bash
pytest tests/ -v --cov=app
```

## 📡 API Endpoints

### Health & Status
- `GET /` - Service status
- `GET /health` - Full health check (all services)

### Rate Limiting & Quota
- `GET /api/quota/users/{user_id}` - Get user quota usage
- `GET /api/quota/users/{user_id}/check` - Check if user is rate limited
- `POST /api/quota/users/{user_id}/reset` - Reset user quota (admin)

## 🏗️ Architecture

### Message Processing Flow
```
Message (RabbitMQ)
    ↓
Validate Schema (Pydantic)
    ↓
Check Idempotency (Redis)
    ↓
Check Rate Limit (Redis)
    ↓
Circuit Breaker Check
    ↓
Send via FCM (Firebase)
    ↓
Persist to Database (PostgreSQL)
    ↓
Log Event (JSON Logs)
    ↓
Response/Retry
```

### Resilience Patterns
- **Idempotency**: Prevents duplicate processing with 24-hour TTL
- **Circuit Breaker**: Automatic failover when FCM fails repeatedly
- **Retry Logic**: Exponential backoff (2^n seconds, max 3 attempts)
- **Dead Letter Queue**: Routes permanent failures for manual review
- **Rate Limiting**: Prevents notification spam per user

## 📁 Project Structure

```
notification-push-service/
├── app/
│   ├── main.py                    # FastAPI app with lifespan
│   ├── config.py                  # Configuration management
│   ├── worker.py                  # RabbitMQ consumer
│   ├── logging_config.py          # Structured JSON logging
│   ├── models/
│   │   └── schemas.py             # Pydantic validation
│   ├── services/
│   │   ├── database.py            # PostgreSQL persistence
│   │   ├── push_provider.py       # FCM integration
│   │   ├── rabbitmq.py            # RabbitMQ setup
│   │   ├── idempotency.py         # Deduplication
│   │   ├── retry.py               # Retry logic
│   │   ├── circuit_breaker.py     # Circuit breaker
│   │   ├── rate_limiter.py        # Rate limiting
│   │   ├── token_validator.py     # Token validation
│   │   └── user_client.py         # User service client
│   └── api/
│       ├── health.py              # Health endpoint
│       └── quota.py               # Quota endpoints
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   └── test_push_flow.py          # Test suite
├── docker-compose.yml             # Local environment
├── Dockerfile                     # Container image
├── requirements.txt               # Dependencies
├── .github/workflows/ci-cd.yml    # GitHub Actions
└── README.md                      # This file
```

## 🔧 Configuration

### Environment Variables

**Required for Firebase:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json
```

**Service Configuration:**
```bash
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/notifications
LOG_LEVEL=INFO
```

## 📊 Example Payload

Send a notification via RabbitMQ:

```json
{
  "notification_id": "notif-123",
  "idempotency_key": "idem-456",
  "user_id": "user-789",
  "platform": "android",
  "title": "Hello!",
  "body": "You have a new message",
  "device_tokens": ["fcm-token-1", "fcm-token-2"],
  "data": {
    "action": "open_app",
    "target": "/messages"
  },
  "ttl_seconds": 3600,
  "attempts": 0
}
```

## 🧪 Testing

Run the full test suite with coverage:

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=html

# Specific test class
pytest tests/test_push_flow.py::TestMessageValidation -v
```

## 📝 Logging

All logs are structured JSON with correlation IDs:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Push sent successfully",
  "service": "notification-push-service",
  "notification_id": "notif-123",
  "idempotency_key": "idem-456",
  "user_id": "user-789"
}
```

Filter logs by notification:
```bash
docker-compose logs push-service | grep "notification_id=notif-123"
```

## 🚢 Docker Deployment

### Build Image
```bash
docker build -t notification-push-service:latest .
```

### Run Container
```bash
docker run -d \
  --name push-service \
  -e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/ \
  -e REDIS_URL=redis://redis:6379/0 \
  -e DATABASE_URL=postgresql://postgres:postgres@postgres:5432/notifications \
  -e LOG_LEVEL=INFO \
  -p 8000:8000 \
  notification-push-service:latest
```

## 🔒 Security

- ✅ Input validation with Pydantic schemas
- ✅ Rate limiting against notification spam
- ✅ Idempotency against duplicate processing
- ✅ Environment-based configuration (no hardcoded secrets)
- ✅ Firebase credentials via `GOOGLE_APPLICATION_CREDENTIALS`
- ✅ Full audit trail with correlation IDs
- ✅ CI/CD security scanning with Trivy

## 🛠️ Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs push-service

# Verify all services are running
docker-compose ps
```

### Database connection error
```bash
# Connect directly to database
docker exec -it notification-postgres psql -U postgres -c "SELECT version();"
```

### Rate limit issues
```bash
# Check user quota
curl http://localhost:8080/api/quota/users/user-123

# Reset quota
curl -X POST http://localhost:8080/api/quota/users/user-123/reset
```

### Firebase not initialized
- Service falls back to mock mode if Firebase credentials are missing
- Set `GOOGLE_APPLICATION_CREDENTIALS` to enable real FCM integration
- Check logs for initialization errors

## 📈 Performance

- **Connection Pool**: 5-20 PostgreSQL connections
- **Max Tokens per Request**: 500 (FCM limit)
- **Rate Limit**: 100 notifications per user per hour
- **Circuit Breaker**: Opens after 3 consecutive failures
- **Idempotency TTL**: 24 hours

## 🔄 CI/CD

GitHub Actions automatically:
- Runs linting (Flake8, Ruff)
- Executes test suite with coverage
- Builds Docker image
- Scans for security vulnerabilities (Trivy)
- Publishes to GitHub Container Registry

View workflow: `.github/workflows/ci-cd.yml`

## 📚 Key Technologies

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI + Uvicorn |
| Language | Python 3.11 |
| Message Queue | RabbitMQ |
| Cache | Redis |
| Database | PostgreSQL |
| Push Provider | Firebase Admin |
| Testing | pytest + asyncio |
| Linting | Flake8 + Ruff |
| Container | Docker + Docker Compose |

## 📞 Support

- Check `docker-compose logs push-service` for error messages
- Review tests in `tests/` for usage examples
- Verify configuration in `app/config.py`
- Check health endpoint: `GET /health`

## 📄 License

[Add your license here]

---

**Status**: ✅ Production Ready
