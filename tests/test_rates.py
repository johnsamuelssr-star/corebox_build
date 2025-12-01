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


def test_create_rate_entry():
    client = TestClient(app)
    token = register_and_login(client, "rate1@example.com", "secret")
    resp = client.post(
        "/rates",
        json={"rate_per_hour": 75.0, "effective_at": "2025-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["rate_per_hour"] == 75.0


def test_list_rate_history_per_user():
    client = TestClient(app)
    token_a = register_and_login(client, "rate2a@example.com", "secret")
    token_b = register_and_login(client, "rate2b@example.com", "secret")

    client.post(
        "/rates",
        json={"rate_per_hour": 70.0, "effective_at": "2025-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    client.post(
        "/rates",
        json={"rate_per_hour": 90.0, "effective_at": "2025-01-02T00:00:00Z"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    resp_a = client.get("/rates", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/rates", headers={"Authorization": f"Bearer {token_b}"})
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["rate_per_hour"] == 70.0
    assert resp_b.json()[0]["rate_per_hour"] == 90.0


def test_current_rate_logic():
    client = TestClient(app)
    token = register_and_login(client, "rate3@example.com", "secret")
    client.post(
        "/rates",
        json={"rate_per_hour": 50.0, "effective_at": "2020-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/rates",
        json={"rate_per_hour": 100.0, "effective_at": "2030-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get("/rates/current", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    # Future rate not active yet; should return 50.0
    assert data["rate_per_hour"] == 50.0


def test_session_autofills_rate():
    client = TestClient(app)
    token = register_and_login(client, "rate4@example.com", "secret")
    student_resp = client.post(
        "/students",
        json={"parent_name": "P", "student_name": "S"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = student_resp.json()["id"]
    client.post(
        "/rates",
        json={"rate_per_hour": 120.0, "effective_at": "2020-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["rate_per_hour"] == 120.0
    assert data["cost_total"] == 120.0


def test_manual_rate_override():
    client = TestClient(app)
    token = register_and_login(client, "rate5@example.com", "secret")
    student_resp = client.post(
        "/students",
        json={"parent_name": "P", "student_name": "S"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = student_resp.json()["id"]
    client.post(
        "/rates",
        json={"rate_per_hour": 200.0, "effective_at": "2020-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Science",
            "duration_minutes": 30,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "rate_per_hour": 50.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["rate_per_hour"] == 50.0
    assert data["cost_total"] == 25.0
