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


def test_parents_post_and_list_are_owner_scoped():
    client = TestClient(app)
    token_a = register_and_login(client, "ownerA@example.com", "secret")
    token_b = register_and_login(client, "ownerB@example.com", "secret")

    payload = {
        "email": "scopedparent@example.com",
        "first_name": "Scoped",
        "last_name": "Parent",
    }
    resp_create = client.post("/parents", json=payload, headers={"Authorization": f"Bearer {token_a}"})
    assert resp_create.status_code in (200, 201)

    resp_list_a = client.get("/parents", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_list_a.status_code == 200
    assert any(p["email"] == payload["email"] for p in resp_list_a.json())

    resp_list_b = client.get("/parents", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_list_b.status_code == 200
    assert all(p["email"] != payload["email"] for p in resp_list_b.json())
