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


def test_owner_can_create_parent():
    client = TestClient(app)
    token = register_and_login(client, "ownercreate@example.com", "secret")

    payload = {
        "email": "newparent@example.com",
        "first_name": "New",
        "last_name": "Parent",
        "phone": "555-1111",
        "notes": "created via test",
    }

    resp = client.post("/parents", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["email"] == payload["email"]
    assert data["first_name"] == payload["first_name"]
    assert data["last_name"] == payload["last_name"]
