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


def create_family(client: TestClient, token: str, parent_email: str, rate_plan: str, student_name: str):
    payload = {
        "parent": {
            "first_name": "Parent",
            "last_name": "Plan",
            "email": parent_email,
            "rate_plan": rate_plan,
        },
        "students": [
            {"parent_name": "Parent Plan", "student_name": student_name, "grade_level": 4},
        ],
    }
    resp = client.post("/enrollments/family", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    body = resp.json()
    return body["parent"]["id"], body["students"][0]["id"]


def test_session_amounts_follow_parent_rate_plan():
    client = TestClient(app)
    token = register_and_login(client, "planrates@example.com", "secret")

    client.put(
        "/settings/rates",
        json={
            "hourly_rate": "0",
            "half_hour_rate": "0",
            "regular_rate_60": "60",
            "regular_rate_45": "45",
            "regular_rate_30": "30",
            "discount_rate_60": "55",
            "discount_rate_45": "40",
            "discount_rate_30": "25",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    _, student_reg = create_family(client, token, "reg@example.com", "regular", "Reg Student")
    _, student_disc = create_family(client, token, "disc@example.com", "discount", "Disc Student")

    cases = [
        (student_reg, 60, Decimal("60")),
        (student_reg, 45, Decimal("45")),
        (student_reg, 30, Decimal("30")),
        (student_disc, 60, Decimal("55")),
        (student_disc, 45, Decimal("40")),
        (student_disc, 30, Decimal("25")),
    ]

    for sid, duration, expected in cases:
        resp = client.post(
            "/sessions",
            json={
                "student_id": sid,
                "subject": "Math",
                "duration_minutes": duration,
                "session_date": "2030-01-01T10:00:00Z",
                "start_time": "10:00:00",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (200, 201)
        assert Decimal(str(resp.json()["cost_total"])) == expected


def test_session_duration_validation():
    client = TestClient(app)
    token = register_and_login(client, "planrates2@example.com", "secret")
    create_family(client, token, "reg2@example.com", "regular", "Reg2 Student")

    resp = client.post(
        "/sessions",
        json={
            "student_id": 1,
            "subject": "Math",
            "duration_minutes": 20,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Unsupported session duration" in resp.json()["detail"]
