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
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_update_parent_rate_plan():
    client = TestClient(app)
    token = register_and_login(client, "owner@example.com", "secret")

    create_resp = client.post(
        "/parents",
        json={"email": "parent@example.com", "first_name": "P", "last_name": "One"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code in (200, 201)
    parent_id = create_resp.json()["id"]
    assert create_resp.json()["rate_plan"] == "regular"

    update_resp = client.put(
        f"/parents/{parent_id}",
        json={"rate_plan": "discount"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["rate_plan"] == "discount"

    detail_resp = client.get(f"/parents/{parent_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == 200
    assert detail_resp.json()["rate_plan"] == "discount"
