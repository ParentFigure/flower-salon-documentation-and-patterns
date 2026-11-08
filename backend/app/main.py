from fastapi import FastAPI

from app.api.routes import (
    auth,
    bouquets,
    delivery_methods,
    flowers,
    health,
    loyalty,
    notifications,
    occasions,
    orders,
    packaging,
    profile,
    salons,
)

app = FastAPI(
    title="Flower Salon Network API",
    version="1.0.1",
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(bouquets.router, prefix="/api")
app.include_router(flowers.router, prefix="/api")
app.include_router(salons.router, prefix="/api")
app.include_router(delivery_methods.router, prefix="/api")
app.include_router(occasions.router, prefix="/api")
app.include_router(packaging.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(loyalty.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
