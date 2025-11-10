from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="notification-push-service", version="1.0.0")

@app.get("/")
def index():
    return {"message": "Push Service API running"}

app.include_router(health_router)

# You can run this separately: uvicorn app.main:app --reload
