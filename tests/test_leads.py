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


def test_create_lead_success():
    client = TestClient(app)
    token = register_and_login(client, "lead@example.com", "secret")
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 5,
        "status": "new",
        "notes": "Interested",
    }
    response = client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    for key in ["parent_name", "student_name", "grade_level", "status", "notes"]:
        assert data[key] == payload[key]
    assert isinstance(data.get("id"), int)


def test_list_leads_returns_user_leads():
    client = TestClient(app)
    token = register_and_login(client, "list@example.com", "secret")
    payload = {
        "parent_name": "Parent2",
        "student_name": "Student2",
        "grade_level": 6,
        "status": "contacted",
        "notes": None,
    }
    client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})
    response = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["parent_name"] == payload["parent_name"]


def test_create_lead_requires_auth():
    client = TestClient(app)
    payload = {
        "parent_name": "NoAuth",
        "student_name": "Student",
        "grade_level": 4,
        "status": "new",
        "notes": None,
    }
    response = client.post("/leads", json=payload)
    assert response.status_code == 401


def test_invalid_status_rejected():
    client = TestClient(app)
    token = register_and_login(client, "badstatus@example.com", "secret")
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 3,
        "status": "invalid",
        "notes": None,
    }
    response = client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "a@example.com", "secret")
    token_b = register_and_login(client, "b@example.com", "secret")

    payload = {
        "parent_name": "ParentA",
        "student_name": "StudentA",
        "grade_level": 2,
        "status": "new",
        "notes": None,
    }
    client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token_a}"})

    response_b = client.get("/leads", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert data_b == []
