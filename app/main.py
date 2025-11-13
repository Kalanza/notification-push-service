from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.health import router as health_router
from app.api.quota import router as quota_router
from app.services.database import init_db, db_pool
from app.logging_config import configure_logging, get_logger
from app.config import settings
from utils.etcd_service import etcd_service

configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown event handler"""
    # Startup
    logger.info("🚀 Starting notification-push-service")
    try:
        await init_db()
        logger.info("✅ Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down notification-push-service")
    await db_pool.disconnect()


app = FastAPI(
    title="notification-push-service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def index():
    return {"message": "Push Service API running"}


app.include_router(health_router)
app.include_router(quota_router)


@app.on_event("startup")
async def startup_event():
    """Register service with etcd on startup"""
    await etcd_service.register_service(
        "push-service", 
        "push-service-001", 
        "push-service",  # Docker service name
        8000
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Deregister service from etcd on shutdown"""
    await etcd_service.deregister_service("push-service", "push-service-001")

