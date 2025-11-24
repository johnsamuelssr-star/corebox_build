import pytest
from decimal import Decimal
from datetime import datetime
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


def create_student(client: TestClient, token: str, parent: str, student: str):
    resp = client.post(
        "/students",
        json={"parent_name": parent, "student_name": student},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int, duration: int, rate: float = 80.0):
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": duration,
            "session_date": "2030-01-01T10:00:00Z",
            "rate_per_hour": rate,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def test_generate_invoice_creates_invoice_and_items():
    client = TestClient(app)
    token = register_and_login(client, "inv1@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")
    create_session(client, token, student_id, 60, 80.0)
    create_session(client, token, student_id, 30, 80.0)

    resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["owner_id"]
    assert data["student_id"] == student_id
    assert data["total_amount"] == "120.00" or data["total_amount"] == 120.0

    list_resp = client.get("/invoices", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert any(inv["id"] == data["id"] for inv in list_resp.json())


def test_generate_invoice_returns_400_if_no_billable_sessions():
    client = TestClient(app)
    token = register_and_login(client, "inv2@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_list_invoices_is_owner_scoped():
    client = TestClient(app)
    token_a = register_and_login(client, "inv3a@example.com", "secret")
    token_b = register_and_login(client, "inv3b@example.com", "secret")

    student_a = create_student(client, token_a, "ParentA", "StudentA")
    create_session(client, token_a, student_a, 60, 80.0)
    inv_a = client.post(f"/invoices/{student_a}/generate", headers={"Authorization": f"Bearer {token_a}"}).json()

    student_b = create_student(client, token_b, "ParentB", "StudentB")
    create_session(client, token_b, student_b, 60, 80.0)
    client.post(f"/invoices/{student_b}/generate", headers={"Authorization": f"Bearer {token_b}"})

    resp = client.get("/invoices", headers={"Authorization": f"Bearer {token_a}"})
    ids = [inv["id"] for inv in resp.json()]
    assert inv_a["id"] in ids
    resp_other = client.get(f"/invoices/{inv_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_other.status_code == 404


def test_update_invoice_status_and_due_date():
    client = TestClient(app)
    token = register_and_login(client, "inv4@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")
    create_session(client, token, student_id, 60, 80.0)
    inv = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"}).json()

    new_due = "2031-01-01T00:00:00Z"
    resp = client.patch(
        f"/invoices/{inv['id']}",
        json={"status": "sent", "due_date": new_due},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["due_date"].startswith("2031-01-01")

    # Cross-owner patch should fail
    token_other = register_and_login(client, "inv4b@example.com", "secret")
    resp_other = client.patch(
        f"/invoices/{inv['id']}",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert resp_other.status_code == 404
