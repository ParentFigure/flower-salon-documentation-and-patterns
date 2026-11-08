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


def auth_headers(SessionLocal, role: UserRole, suffix: str = "user") -> dict[str, str]:
    with SessionLocal() as db:
        user = User(
            email=f"catalog-{role.value}-{suffix}@example.com",
            password_hash="hashed-password",
            role=role,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def create_occasion(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Birthday",
    slug: str = "birthday",
    active: bool = True,
):
    return client.post(
        "/api/occasions",
        headers=headers,
        json={
            "name": name,
            "slug": slug,
            "description": f"Bouquets for {name}",
            "is_active": active,
        },
    )


def create_packaging(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Craft paper",
    price: str = "75.00",
    active: bool = True,
):
    return client.post(
        "/api/packaging",
        headers=headers,
        json={
            "name": name,
            "description": f"{name} wrapping",
            "price": price,
            "is_active": active,
        },
    )


def test_admin_can_create_occasion_and_public_can_read_it():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        created = create_occasion(client, headers)
        assert created.status_code == 201
        occasion = created.json()

        detail = client.get(f"/api/occasions/{occasion['id']}")
        assert detail.status_code == 200
        assert detail.json()["slug"] == "birthday"

    app.dependency_overrides.clear()


def test_public_occasion_list_contains_only_active_items():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        create_occasion(client, headers, name="Birthday", slug="birthday")
        create_occasion(
            client,
            headers,
            name="Archived Event",
            slug="archived-event",
            active=False,
        )

        response = client.get("/api/occasions")
        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Birthday"]

    app.dependency_overrides.clear()


def test_occasion_writes_require_admin():
    client, SessionLocal = make_client()
    client_headers = auth_headers(SessionLocal, UserRole.CLIENT)
    payload = {
        "name": "Wedding",
        "slug": "wedding",
        "description": None,
        "is_active": True,
    }

    with client:
        assert client.post("/api/occasions", json=payload).status_code == 401
        assert client.post(
            "/api/occasions", headers=client_headers, json=payload
        ).status_code == 403

    app.dependency_overrides.clear()


def test_duplicate_occasion_name_or_slug_returns_409():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        assert create_occasion(client, headers).status_code == 201

        same_name = create_occasion(
            client,
            headers,
            name="Birthday",
            slug="birthday-party",
        )
        same_slug = create_occasion(
            client,
            headers,
            name="Birthday Party",
            slug="birthday",
        )

        assert same_name.status_code == 409
        assert same_slug.status_code == 409

    app.dependency_overrides.clear()


def test_admin_can_update_and_delete_occasion():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        occasion = create_occasion(client, headers).json()
        updated = client.put(
            f"/api/occasions/{occasion['id']}",
            headers=headers,
            json={
                "name": "Birthday Party",
                "slug": "birthday-party",
                "description": "Updated",
                "is_active": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["slug"] == "birthday-party"

        deleted = client.delete(
            f"/api/occasions/{occasion['id']}", headers=headers
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/occasions/{occasion['id']}").status_code == 404

    app.dependency_overrides.clear()


def test_invalid_occasion_slug_returns_422():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = create_occasion(
            client,
            headers,
            name="Bad Slug",
            slug="Bad Slug!",
        )
        assert response.status_code == 422

    app.dependency_overrides.clear()


def test_missing_occasion_returns_404():
    client, _ = make_client()
    with client:
        response = client.get("/api/occasions/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Occasion not found"
    app.dependency_overrides.clear()


def test_admin_can_create_packaging_and_public_can_read_it():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        created = create_packaging(client, headers)
        assert created.status_code == 201
        packaging = created.json()
        assert Decimal(str(packaging["price"])) == Decimal("75.00")

        detail = client.get(f"/api/packaging/{packaging['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Craft paper"

    app.dependency_overrides.clear()


def test_public_packaging_list_contains_only_active_items():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        create_packaging(client, headers, name="Craft paper", price="75.00")
        create_packaging(
            client,
            headers,
            name="Old box",
            price="150.00",
            active=False,
        )

        response = client.get("/api/packaging")
        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Craft paper"]

    app.dependency_overrides.clear()


def test_packaging_writes_require_admin():
    client, SessionLocal = make_client()
    client_headers = auth_headers(SessionLocal, UserRole.CLIENT)
    payload = {
        "name": "Gift box",
        "description": None,
        "price": "150.00",
        "is_active": True,
    }

    with client:
        assert client.post("/api/packaging", json=payload).status_code == 401
        assert client.post(
            "/api/packaging", headers=client_headers, json=payload
        ).status_code == 403

    app.dependency_overrides.clear()


def test_duplicate_packaging_name_returns_409():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        assert create_packaging(client, headers).status_code == 201
        duplicate = create_packaging(client, headers)
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "Packaging option with this name already exists"

    app.dependency_overrides.clear()


def test_admin_can_update_and_delete_packaging():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        packaging = create_packaging(client, headers).json()
        updated = client.put(
            f"/api/packaging/{packaging['id']}",
            headers=headers,
            json={
                "name": "Premium gift box",
                "description": "Rigid box",
                "price": "180.00",
                "is_active": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Premium gift box"
        assert Decimal(str(updated.json()["price"])) == Decimal("180.00")

        deleted = client.delete(
            f"/api/packaging/{packaging['id']}", headers=headers
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/packaging/{packaging['id']}").status_code == 404

    app.dependency_overrides.clear()


def test_negative_packaging_price_returns_422():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = create_packaging(client, headers, price="-1.00")
        assert response.status_code == 422

    app.dependency_overrides.clear()


def test_missing_packaging_returns_404():
    client, _ = make_client()
    with client:
        response = client.get("/api/packaging/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Packaging option not found"
    app.dependency_overrides.clear()
