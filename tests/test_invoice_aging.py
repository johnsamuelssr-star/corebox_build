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


def set_invoice_due_and_balance(invoice_id: int, due_dt: datetime, balance: Decimal, status: str | None = None):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        inv.due_date = due_dt
        inv.balance_due = balance
        if status is not None:
            inv.status = status
        db.commit()
    finally:
        db.close()


def test_aging_buckets_basic():
    client = TestClient(app)
    token = register_and_login(client, "aging1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)

    today = datetime.now(timezone.utc).date()

    # Create copies for different buckets by regenerating invoices
    invoices = [invoice]
    balances = [Decimal("100.00"), Decimal("200.00"), Decimal("300.00"), Decimal("400.00"), Decimal("500.00")]
    days_offsets = [0, 10, 45, 75, 120]  # current, 1-30, 31-60, 61-90, 90+

    # Create four more invoices
    for _ in range(4):
        create_session(client, token, student_id, 50.0, 60)
        invoices.append(generate_invoice(client, token, student_id))

    for inv, balance, days in zip(invoices, balances, days_offsets):
        due_date = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
        set_invoice_due_and_balance(inv["id"], due_date, balance)

    resp = client.get("/invoices/aging-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    buckets = data["buckets"]
    assert buckets["current"]["count"] == 1
    assert buckets["current"]["total_balance"] == "100.00"
    assert buckets["days_1_30"]["count"] == 1
    assert buckets["days_1_30"]["total_balance"] == "200.00"
    assert buckets["days_31_60"]["count"] == 1
    assert buckets["days_31_60"]["total_balance"] == "300.00"
    assert buckets["days_61_90"]["count"] == 1
    assert buckets["days_61_90"]["total_balance"] == "400.00"
    assert buckets["days_90_plus"]["count"] == 1
    assert buckets["days_90_plus"]["total_balance"] == "500.00"


def test_aging_ignores_fully_paid_invoices():
    client = TestClient(app)
    token = register_and_login(client, "aging2@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 80.0, 60)
    unpaid_inv = generate_invoice(client, token, student_id)

    create_session(client, token, student_id, 90.0, 60)
    paid_inv = generate_invoice(client, token, student_id)

    today = datetime.now(timezone.utc).date()
    set_invoice_due_and_balance(
        unpaid_inv["id"],
        datetime.combine(today - timedelta(days=15), datetime.min.time(), tzinfo=timezone.utc),
        Decimal("80.00"),
    )
    set_invoice_due_and_balance(
        paid_inv["id"],
        datetime.combine(today - timedelta(days=15), datetime.min.time(), tzinfo=timezone.utc),
        Decimal("0.00"),
        status="paid",
    )

    resp = client.get("/invoices/aging-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    buckets = data["buckets"]
    assert buckets["days_1_30"]["count"] == 1
    assert buckets["days_1_30"]["total_balance"] == "80.00"


def test_aging_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "aging3a@example.com", "secret")
    token_b = register_and_login(client, "aging3b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 50.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 60.0, 60)
    inv_b = generate_invoice(client, token_b, student_b)

    today = datetime.now(timezone.utc).date()
    set_invoice_due_and_balance(
        inv_a["id"],
        datetime.combine(today - timedelta(days=10), datetime.min.time(), tzinfo=timezone.utc),
        Decimal("50.00"),
    )
    set_invoice_due_and_balance(
        inv_b["id"],
        datetime.combine(today - timedelta(days=120), datetime.min.time(), tzinfo=timezone.utc),
        Decimal("60.00"),
    )

    resp_a = client.get("/invoices/aging-summary", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["buckets"]["days_1_30"]["total_balance"] == "50.00"
    assert data_a["buckets"]["days_90_plus"]["total_balance"] == "0.00"

    resp_b = client.get("/invoices/aging-summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["buckets"]["days_90_plus"]["total_balance"] == "60.00"
    assert data_b["buckets"]["days_1_30"]["total_balance"] == "0.00"


def test_aging_handles_no_invoices():
    client = TestClient(app)
    token = register_and_login(client, "aging4@example.com", "secret")

    resp = client.get("/invoices/aging-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    for bucket in data["buckets"].values():
        assert bucket["count"] == 0
        assert bucket["total_balance"] == "0.00"
