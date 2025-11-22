import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_me_returns_current_user():
    client = TestClient(app)
    token = register_and_login(client, "me@example.com", "secret")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert isinstance(data.get("id"), int)


def test_me_without_token_returns_401():
    client = TestClient(app)
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    client = TestClient(app)
    client.post("/auth/register", json={"email": "badtoken@example.com", "password": "secret"})
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
