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


def test_aging_summary_basic():
    client = TestClient(app)
    token = register_and_login(client, "agingrep1@example.com", "secret")
    student_id = create_student(client, token)

    today = datetime(2030, 6, 1, tzinfo=timezone.utc)
    offsets = [0, 10, 45, 75, 120]
    balances = [Decimal("100.00"), Decimal("200.00"), Decimal("300.00"), Decimal("400.00"), Decimal("500.00")]
    invoices = []

    for _ in offsets:
        create_session(client, token, student_id, 50.0, 60)
        invoices.append(generate_invoice(client, token, student_id))

    for inv, days, bal in zip(invoices, offsets, balances):
        due_date = today - timedelta(days=days)
        set_invoice_due_and_balance(inv["id"], due_date, bal)

    resp = client.get(
        "/admin/reports/aging-summary",
        params={"as_of": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    totals = data["totals"]
    assert totals["current"] == "100.00"
    assert totals["days_1_30"] == "200.00"
    assert totals["days_31_60"] == "300.00"
    assert totals["days_61_90"] == "400.00"
    assert totals["days_90_plus"] == "500.00"
    assert len(data["students"]) == 1
    stu = data["students"][0]
    assert stu["buckets"]["days_90_plus"] == "500.00"


def test_aging_summary_ignores_fully_paid():
    client = TestClient(app)
    token = register_and_login(client, "agingrep2@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 1, tzinfo=timezone.utc)

    create_session(client, token, student_id, 80.0, 60)
    inv_unpaid = generate_invoice(client, token, student_id)
    set_invoice_due_and_balance(inv_unpaid["id"], today - timedelta(days=20), Decimal("80.00"))

    create_session(client, token, student_id, 90.0, 60)
    inv_paid = generate_invoice(client, token, student_id)
    set_invoice_due_and_balance(inv_paid["id"], today - timedelta(days=40), Decimal("0.00"), status="paid")

    resp = client.get(
        "/admin/reports/aging-summary",
        params={"as_of": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    totals = data["totals"]
    assert totals["days_1_30"] == "80.00"
    assert totals["days_31_60"] == "0.00"


def test_aging_summary_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "agingrep3a@example.com", "secret")
    token_b = register_and_login(client, "agingrep3b@example.com", "secret")
    today = datetime(2030, 6, 1, tzinfo=timezone.utc)

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 60.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)
    set_invoice_due_and_balance(inv_a["id"], today - timedelta(days=15), Decimal("60.00"))

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 70.0, 60)
    inv_b = generate_invoice(client, token_b, student_b)
    set_invoice_due_and_balance(inv_b["id"], today - timedelta(days=95), Decimal("70.00"))

    resp_a = client.get(
        "/admin/reports/aging-summary",
        params={"as_of": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["totals"]["days_1_30"] == "60.00"
    assert data_a["totals"]["days_90_plus"] == "0.00"

    resp_b = client.get(
        "/admin/reports/aging-summary",
        params={"as_of": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["totals"]["days_90_plus"] == "70.00"
    assert data_b["totals"]["days_1_30"] == "0.00"


def test_aging_summary_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "agingrep4@example.com", "secret")

    resp = client.get("/admin/reports/aging-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    totals = data["totals"]
    assert totals["current"] == "0.00"
    assert totals["days_1_30"] == "0.00"
    assert totals["days_31_60"] == "0.00"
    assert totals["days_61_90"] == "0.00"
    assert totals["days_90_plus"] == "0.00"
