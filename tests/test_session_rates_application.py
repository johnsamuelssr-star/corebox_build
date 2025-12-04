import pytest
from decimal import Decimal
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


def create_student(client: TestClient, token: str):
    resp = client.post(
        "/students",
        json={"parent_name": "Parent", "student_name": "Student"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_session_cost_uses_settings_defaults_when_missing_rate():
    client = TestClient(app)
    token = register_and_login(client, "sessrates1@example.com", "secret")
    student_id = create_student(client, token)

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
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert Decimal(str(data["cost_total"])) == Decimal("60.00")


def test_session_cost_uses_half_hour_rate_for_30_minutes():
    client = TestClient(app)
    token = register_and_login(client, "sessrates2@example.com", "secret")
    student_id = create_student(client, token)
    client.put(
        "/settings/rates",
        json={
            "hourly_rate": "0",
            "half_hour_rate": "0",
            "regular_rate_60": "100",
            "regular_rate_45": "80",
            "regular_rate_30": "70",
            "discount_rate_60": "90",
            "discount_rate_45": "70",
            "discount_rate_30": "50",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 30,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert Decimal(str(data["cost_total"])) == Decimal("70.00")


def test_session_cost_fallback_for_other_durations():
    client = TestClient(app)
    token = register_and_login(client, "sessrates3@example.com", "secret")
    student_id = create_student(client, token)
    client.put(
        "/settings/rates",
        json={
            "hourly_rate": "0",
            "half_hour_rate": "0",
            "regular_rate_60": "120",
            "regular_rate_45": "90",
            "regular_rate_30": "60",
            "discount_rate_60": "110",
            "discount_rate_45": "80",
            "discount_rate_30": "50",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Science",
            "duration_minutes": 90,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_session_creation_honors_explicit_cost_total():
    client = TestClient(app)
    token = register_and_login(client, "sessrates4@example.com", "secret")
    student_id = create_student(client, token)
    client.put(
        "/settings/rates",
        json={
            "hourly_rate": "0",
            "half_hour_rate": "0",
            "regular_rate_60": "100",
            "regular_rate_45": "80",
            "regular_rate_30": "60",
            "discount_rate_60": "90",
            "discount_rate_45": "70",
            "discount_rate_30": "50",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "History",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "cost_total": 25.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert Decimal(str(data["cost_total"])) == Decimal("25.00")
