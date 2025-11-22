import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_successful_registration_returns_user():
    client = TestClient(app)
    payload = {"email": "user@example.com", "password": "secret"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert "password" not in data
    assert "hashed_password" not in data
    assert isinstance(data.get("id"), int)


def test_duplicate_email_returns_400():
    client = TestClient(app)
    payload = {"email": "dup@example.com", "password": "secret"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_user_persisted_in_db():
    client = TestClient(app)
    payload = {"email": "persist@example.com", "password": "secret"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == payload["email"]).first()
        assert user is not None
        assert user.email == payload["email"]
        assert user.hashed_password and user.hashed_password != payload["password"]
