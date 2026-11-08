from app.models.client import Client
from app.models.user import User, UserRole


def test_user_defaults():
    user = User(
        email="client@example.com",
        password_hash="hashed-password",
    )

    assert user.email == "client@example.com"
    assert user.password_hash == "hashed-password"


def test_user_role_values():
    assert UserRole.CLIENT.value == "client"
    assert UserRole.ADMIN.value == "admin"


def test_client_profile_can_be_linked_to_user():
    user = User(
        email="client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(full_name="Test Client", phone="+380000000000")
    user.client = client

    assert user.client is client
    assert client.user is user
