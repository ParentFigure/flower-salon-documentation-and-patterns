import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_admin, require_client
from app.core.security import verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User, UserRole


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def register(client: TestClient, **overrides):
    payload = {
        "email": "marta@example.com",
        "password": "strong-password-123",
        "full_name": "Marta Client",
        "phone": "+380000000100",
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def login(client: TestClient, **overrides):
    payload = {
        "email": "marta@example.com",
        "password": "strong-password-123",
    }
    payload.update(overrides)
    return client.post("/api/auth/login", json=payload)


def test_register_client_returns_201_and_client_profile():
    client, _ = make_client()
    with client:
        response = register(client)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "marta@example.com"
        assert data["role"] == "client"
        assert data["client_id"] is not None
    app.dependency_overrides.clear()


def test_registration_hashes_password_in_database():
    client, SessionLocal = make_client()
    with client:
        assert register(client).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "marta@example.com"))
        assert user is not None
        assert user.password_hash != "strong-password-123"
        assert verify_password("strong-password-123", user.password_hash)
    app.dependency_overrides.clear()


def test_duplicate_email_returns_409_case_insensitively():
    client, _ = make_client()
    with client:
        assert register(client).status_code == 201
        response = register(client, email="MARTA@example.com")
        assert response.status_code == 409
        assert response.json()["detail"] == "Email is already registered"
    app.dependency_overrides.clear()


def test_short_password_is_rejected():
    client, _ = make_client()
    with client:
        response = register(client, password="short")
        assert response.status_code == 422
    app.dependency_overrides.clear()


def test_login_returns_bearer_jwt():
    client, _ = make_client()
    with client:
        register(client)
        response = login(client)
        assert response.status_code == 200
        data = response.json()
        assert data["token_type"] == "bearer"
        assert len(data["access_token"].split(".")) == 3
    app.dependency_overrides.clear()


def test_login_with_wrong_password_returns_401():
    client, _ = make_client()
    with client:
        register(client)
        response = login(client, password="wrong-password")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"
    app.dependency_overrides.clear()


def test_login_with_unknown_email_returns_401():
    client, _ = make_client()
    with client:
        response = login(client, email="unknown@example.com")
        assert response.status_code == 401
    app.dependency_overrides.clear()


def test_me_returns_authenticated_user():
    client, _ = make_client()
    with client:
        registered = register(client).json()
        token = login(client).json()["access_token"]
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == registered["id"]
        assert response.json()["client_id"] == registered["client_id"]
    app.dependency_overrides.clear()


def test_me_without_token_returns_401():
    client, _ = make_client()
    with client:
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
    app.dependency_overrides.clear()


def test_me_with_tampered_token_returns_401():
    client, _ = make_client()
    with client:
        register(client)
        token = login(client).json()["access_token"]
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
    app.dependency_overrides.clear()


def test_role_dependencies_allow_only_matching_role():
    admin = User(
        id=1,
        email="admin@example.com",
        password_hash="unused",
        role=UserRole.ADMIN,
        is_active=True,
    )
    regular = User(
        id=2,
        email="client@example.com",
        password_hash="unused",
        role=UserRole.CLIENT,
        is_active=True,
    )

    assert require_admin(admin) is admin
    assert require_client(regular) is regular

    with pytest.raises(HTTPException) as admin_error:
        require_admin(regular)
    assert admin_error.value.status_code == 403

    with pytest.raises(HTTPException) as client_error:
        require_client(admin)
    assert client_error.value.status_code == 403
