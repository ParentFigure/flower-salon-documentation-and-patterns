import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import DeliveryMethod, Occasion, Packaging, Salon, User, UserRole


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), SessionLocal


def seed_user(SessionLocal, role: UserRole, email: str) -> dict[str, str]:
    with SessionLocal() as db:
        user = User(email=email, password_hash="hashed-password", role=role)
        db.add(user)
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def seed_inactive_reference_data(SessionLocal) -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                Packaging(name="Inactive wrap", price=Decimal("10.00"), is_active=False),
                Occasion(name="Inactive event", slug="inactive-event", is_active=False),
                Salon(name="Inactive salon", address="Test address 1", is_active=False),
                DeliveryMethod(
                    code="inactive-delivery",
                    name="Inactive delivery",
                    base_price=Decimal("20.00"),
                    requires_address=True,
                    is_active=False,
                ),
            ]
        )
        db.commit()


def test_admin_reference_endpoints_include_inactive_records():
    client, SessionLocal = make_client()
    admin_headers = seed_user(SessionLocal, UserRole.ADMIN, "refs-admin@example.com")
    seed_inactive_reference_data(SessionLocal)

    with client:
        endpoints = [
            "/api/packaging/admin/all",
            "/api/occasions/admin/all",
            "/api/salons/admin/all",
            "/api/delivery-methods/admin/all",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["is_active"] is False

    app.dependency_overrides.clear()


def test_public_reference_endpoints_still_hide_inactive_records():
    client, SessionLocal = make_client()
    seed_inactive_reference_data(SessionLocal)

    with client:
        for endpoint in ["/api/packaging", "/api/occasions", "/api/salons", "/api/delivery-methods"]:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.json() == []

    app.dependency_overrides.clear()


def test_client_cannot_use_admin_reference_endpoint():
    client, SessionLocal = make_client()
    client_headers = seed_user(SessionLocal, UserRole.CLIENT, "refs-client@example.com")

    with client:
        response = client.get("/api/packaging/admin/all", headers=client_headers)
        assert response.status_code == 403

    app.dependency_overrides.clear()
