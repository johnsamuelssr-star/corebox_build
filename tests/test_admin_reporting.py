from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.invoice import Invoice


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


def set_invoice_created_at(invoice_id: int, dt: datetime):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        inv.created_at = dt
        db.commit()
    finally:
        db.close()


def test_financial_summary_basic():
    client = TestClient(app)
    # First user becomes admin
    token = register_and_login(client, "adminreport1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)
    create_payment(client, token, invoice["id"], "100.00")

    resp = client.get("/admin/reports/financial-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_invoiced"] == "100.00"
    assert data["total_paid"] == "100.00"
    assert data["total_outstanding"] == "0.00"
    assert data["invoice_count"] == 1
    assert data["paid_invoice_count"] == 1
    assert data["unpaid_invoice_count"] == 0


def test_financial_summary_multiple_invoices():
    client = TestClient(app)
    token = register_and_login(client, "adminreport2@example.com", "secret")
    student_id = create_student(client, token)

    # Invoice 1: partially paid
    create_session(client, token, student_id, 100.0, 60)
    inv1 = generate_invoice(client, token, student_id)
    create_payment(client, token, inv1["id"], "50.00")

    # Invoice 2: unpaid
    create_session(client, token, student_id, 200.0, 60)
    inv2 = generate_invoice(client, token, student_id)

    # Invoice 3: fully paid
    create_session(client, token, student_id, 150.0, 60)
    inv3 = generate_invoice(client, token, student_id)
    create_payment(client, token, inv3["id"], "150.00")

    resp = client.get("/admin/reports/financial-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_invoiced"] == "450.00"
    assert data["total_paid"] == "200.00"
    # Outstanding: 50 (inv1) + 200 (inv2) + 0 (inv3)
    assert data["total_outstanding"] == "250.00"
    assert data["invoice_count"] == 3
    assert data["paid_invoice_count"] == 1
    assert data["unpaid_invoice_count"] == 2


def test_financial_summary_date_range():
    client = TestClient(app)
    token = register_and_login(client, "adminreport3@example.com", "secret")
    student_id = create_student(client, token)

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(days=40)
    later = now - timedelta(days=5)

    create_session(client, token, student_id, 100.0, 60)
    inv1 = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv1["id"], earlier)

    create_session(client, token, student_id, 80.0, 60)
    inv2 = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv2["id"], now)
    create_payment(client, token, inv2["id"], "80.00")

    resp = client.get(
        "/admin/reports/financial-summary",
        params={"start_date": (now - timedelta(days=10)).date().isoformat(), "end_date": later.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Only inv2 falls into the range
    assert data["invoice_count"] == 1
    assert data["total_invoiced"] == "80.00"
    assert data["total_paid"] == "80.00"
    assert data["total_outstanding"] == "0.00"


def test_financial_summary_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "adminreport4a@example.com", "secret")
    token_b = register_and_login(client, "adminreport4b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 120.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)
    create_payment(client, token_a, inv_a["id"], "60.00")

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 200.0, 60)
    inv_b = generate_invoice(client, token_b, student_b)

    resp_a = client.get("/admin/reports/financial-summary", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total_invoiced"] == "120.00"
    assert data_a["total_paid"] == "60.00"
    assert data_a["total_outstanding"] == "60.00"

    resp_b = client.get("/admin/reports/financial-summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total_invoiced"] == "200.00"
    assert data_b["total_paid"] == "0.00"
    assert data_b["total_outstanding"] == "200.00"


def test_financial_summary_no_invoices():
    client = TestClient(app)
    token = register_and_login(client, "adminreport5@example.com", "secret")

    resp = client.get("/admin/reports/financial-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoice_count"] == 0
    assert data["total_invoiced"] == "0.00"
    assert data["total_paid"] == "0.00"
    assert data["total_outstanding"] == "0.00"
