from datetime import datetime, timedelta, timezone
from decimal import Decimal

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


def create_session(client: TestClient, token: str, student_id: int, rate: float, duration: int):
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": duration,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
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


def test_activity_summary_basic():
    client = TestClient(app)
    token = register_and_login(client, "activity1@example.com", "secret")
    student_id = create_student(client, token)

    sess1 = create_session(client, token, student_id, 100.0, 60)
    sess2 = create_session(client, token, student_id, 100.0, 60)

    inv1 = generate_invoice(client, token, student_id)
    create_payment(client, token, inv1["id"], "150.00")

    resp = client.get("/admin/reports/activity-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_count"] == 2
    assert data["total_hours"] == "2.00"
    assert data["total_invoiced"] == "200.00"
    assert data["total_paid"] == "150.00"
    assert data["total_outstanding"] == "50.00"
    assert len(data["students"]) == 1
    stu = data["students"][0]
    assert stu["session_count"] == 2
    assert stu["hours"] == "2.00"
    assert stu["total_invoiced"] == "200.00"


def test_activity_summary_date_range_lower_bound():
    client = TestClient(app)
    token = register_and_login(client, "activity2@example.com", "secret")
    student_id = create_student(client, token)

    now = datetime.now(timezone.utc)
    older = now - timedelta(days=30)
    newer = now

    sess_old = create_session(client, token, student_id, 60.0, 60)
    set_session_date(sess_old["id"], older)
    inv_old = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv_old["id"], older)

    sess_new = create_session(client, token, student_id, 80.0, 60)
    set_session_date(sess_new["id"], newer)
    inv_new = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv_new["id"], newer)
    create_payment(client, token, inv_new["id"], "40.00")

    resp = client.get(
        "/admin/reports/activity-summary",
        params={"start_date": (now - timedelta(days=10)).date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Only newer session/invoice should be counted
    assert data["session_count"] == 1
    assert data["total_hours"] == "1.00"
    assert data["total_invoiced"] == "80.00"
    assert data["total_paid"] == "40.00"


def test_activity_summary_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "activity3a@example.com", "secret")
    token_b = register_and_login(client, "activity3b@example.com", "secret")

    student_a = create_student(client, token_a)
    sess_a = create_session(client, token_a, student_a, 50.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)
    create_payment(client, token_a, inv_a["id"], "25.00")

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 70.0, 60)
    inv_b = generate_invoice(client, token_b, student_b)

    resp_a = client.get("/admin/reports/activity-summary", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["session_count"] == 1
    assert data_a["total_invoiced"] == "50.00"
    assert data_a["total_paid"] == "25.00"

    resp_b = client.get("/admin/reports/activity-summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["session_count"] == 1
    assert data_b["total_invoiced"] == "70.00"
    assert data_b["total_paid"] == "0.00"


def test_activity_summary_no_data():
    client = TestClient(app)
    token = register_and_login(client, "activity4@example.com", "secret")

    resp = client.get("/admin/reports/activity-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_count"] == 0
    assert data["total_hours"] == "0.00"
    assert data["total_invoiced"] == "0.00"
    assert data["total_paid"] == "0.00"
    assert data["total_outstanding"] == "0.00"
