from fastapi import FastAPI

from app.api.routes import (
    auth,
    bouquets,
    flowers,
    health,
    loyalty,
    notifications,
    occasions,
    orders,
    packaging,
)

app = FastAPI(
    title="Flower Salon Network API",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(bouquets.router, prefix="/api")
app.include_router(flowers.router, prefix="/api")
app.include_router(occasions.router, prefix="/api")
app.include_router(packaging.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(loyalty.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
