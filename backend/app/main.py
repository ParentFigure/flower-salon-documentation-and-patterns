from fastapi import FastAPI
from app.api.routes import health, bouquets

app = FastAPI(
    title="Flower Salon Network API",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(bouquets.router, prefix="/api")
