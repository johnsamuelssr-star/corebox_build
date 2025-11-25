from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.invoice import Invoice
from backend.app.models.session import Session


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


def create_student(client: TestClient, token: str) -> int:
    resp = client.post(
        "/students",
        json={"parent_name": "Parent", "student_name": "Student"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int, rate: float, duration: int, session_date: str):
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": duration,
            "session_date": session_date,
            "rate_per_hour": rate,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def generate_invoice(client: TestClient, token: str, student_id: int):
    resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def create_payment(client: TestClient, token: str, invoice_id: int, amount: str):
    resp = client.post(
        f"/invoices/{invoice_id}/payments",
        json={"invoice_id": invoice_id, "amount": amount},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


def set_session_date(session_id: int, dt: datetime):
    db = SessionLocal()
    try:
        sess = db.query(Session).filter(Session.id == session_id).first()
        sess.session_date = dt
        db.commit()
    finally:
        db.close()


def set_invoice_created_at(invoice_id: int, dt: datetime):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        inv.created_at = dt
        db.commit()
    finally:
        db.close()


def test_owner_dashboard_summary_basic():
    client = TestClient(app)
    token = register_and_login(client, "dashcard1@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 100.0, 60, "2030-06-01T10:00:00Z")
    create_session(client, token, student_id, 80.0, 90, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    create_payment(client, token, inv["id"], "120.00")
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        "/admin/dashboard/summary",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "financial" in data and "activity" in data and "ar" in data and "pipeline" in data
    assert data["financial"]["total_paid_all_time"] == "120.00"
    assert data["activity"]["total_sessions_all_time"] == 2


def test_owner_dashboard_summary_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "dashcard2@example.com", "secret")
    resp = client.get("/admin/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["financial"]["total_invoiced_all_time"] == "0.00"
    assert data["activity"]["total_sessions_all_time"] == 0


def test_student_dashboard_list_basic():
    client = TestClient(app)
    token = register_and_login(client, "dashcard3@example.com", "secret")
    student_a = create_student(client, token)
    student_b = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_a, 60.0, 60, "2030-06-01T10:00:00Z")
    inv_a = generate_invoice(client, token, student_a)
    create_payment(client, token, inv_a["id"], "60.00")

    create_session(client, token, student_b, 80.0, 60, "2030-06-02T10:00:00Z")
    inv_b = generate_invoice(client, token, student_b)
    set_invoice_created_at(inv_b["id"], today)

    resp = client.get(
        "/admin/dashboard/students",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["students"]) == 2
    stu_map = {s["student_id"]: s for s in data["students"]}
    assert stu_map[student_a]["total_paid_all_time"] == "60.00"
    assert stu_map[student_b]["total_sessions_all_time"] == 1


def test_student_dashboard_list_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "dashcard4@example.com", "secret")
    student_id = create_student(client, token)

    resp = client.get("/admin/dashboard/students", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["students"]) == 1
    row = data["students"][0]
    assert row["total_sessions_all_time"] == 0
    assert row["total_invoiced_all_time"] == "0.00"


def test_dashboard_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "dashcard5a@example.com", "secret")
    token_b = register_and_login(client, "dashcard5b@example.com", "secret")
    student_a = create_student(client, token_a)
    student_b = create_student(client, token_b)

    create_session(client, token_a, student_a, 50.0, 60, "2030-06-01T10:00:00Z")
    inv_a = generate_invoice(client, token_a, student_a)
    create_payment(client, token_a, inv_a["id"], "50.00")

    create_session(client, token_b, student_b, 70.0, 60, "2030-06-02T10:00:00Z")
    inv_b = generate_invoice(client, token_b, student_b)

    resp_a = client.get("/admin/dashboard/summary", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/admin/dashboard/summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_a.status_code == 200 and resp_b.status_code == 200
    data_a = resp_a.json()
    data_b = resp_b.json()
    assert data_a["financial"]["total_invoiced_all_time"] != data_b["financial"]["total_invoiced_all_time"]

    resp_students_a = client.get("/admin/dashboard/students", headers={"Authorization": f"Bearer {token_a}"})
    resp_students_b = client.get("/admin/dashboard/students", headers={"Authorization": f"Bearer {token_b}"})
    assert len(resp_students_a.json()["students"]) == 1
    assert len(resp_students_b.json()["students"]) == 1
