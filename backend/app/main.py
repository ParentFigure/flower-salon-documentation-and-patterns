from fastapi import FastAPI

from app.api.routes import bouquets, health, orders

app = FastAPI(
    title="Flower Salon Network API",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(bouquets.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
