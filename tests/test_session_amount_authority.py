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


def create_parent(client: TestClient, token: str, email: str, rate_plan: str):
    resp = client.post(
        "/parents",
        json={"email": email, "first_name": "Parent", "last_name": "Plan", "rate_plan": rate_plan},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_student_for_parent(client: TestClient, token: str, parent_id: int):
    resp = client.post(
        f"/parents/{parent_id}/students",
        json={"student_name": "Child", "grade_level": 4},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_client_amount_ignored_use_plan_rate():
    client = TestClient(app)
    token = register_and_login(client, "amountauth@example.com", "secret")

    client.put(
        "/settings/rates",
        json={
            "regular_rate_60": "100",
            "regular_rate_45": "90",
            "regular_rate_30": "80",
            "discount_rate_60": "50",
            "discount_rate_45": "40",
            "discount_rate_30": "30",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    parent_reg = create_parent(client, token, "reg@example.com", "regular")
    parent_disc = create_parent(client, token, "disc@example.com", "discount")

    student_reg = create_student_for_parent(client, token, parent_reg)
    student_disc = create_student_for_parent(client, token, parent_disc)

    resp_reg = client.post(
        "/sessions",
        json={
            "student_id": student_reg,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "cost_total": 999,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_reg.status_code in (200, 201)
    resp_reg_json = resp_reg.json()
    assert Decimal(str(resp_reg_json["cost_total"])) == Decimal("100")
    assert resp_reg_json["rate_plan"] == "regular"

    resp_disc = client.post(
        "/sessions",
        json={
            "student_id": student_disc,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "cost_total": 999,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_disc.status_code in (200, 201)
    resp_disc_json = resp_disc.json()
    assert Decimal(str(resp_disc_json["cost_total"])) == Decimal("50")
    assert resp_disc_json["rate_plan"] == "discount"
