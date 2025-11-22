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


def test_protected_ping_requires_auth():
    client = TestClient(app)
    response = client.get("/protected/ping")
    assert response.status_code == 401


def test_protected_ping_rejects_invalid_token():
    client = TestClient(app)
    response = client.get("/protected/ping", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401


def test_protected_ping_with_valid_token():
    client = TestClient(app)
    token = register_and_login(client, "protected@example.com", "secret")
    response = client.get("/protected/ping", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert isinstance(data.get("user_id"), int)
