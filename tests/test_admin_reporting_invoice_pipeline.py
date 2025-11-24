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


def set_invoice_fields(invoice_id: int, *, status: str | None = None, due_date: datetime | None = None, balance: Decimal | None = None):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if status is not None:
            inv.status = status
        if due_date is not None:
            inv.due_date = due_date
        if balance is not None:
            inv.balance_due = balance
        db.commit()
    finally:
        db.close()


def test_invoice_pipeline_basic_statuses():
    client = TestClient(app)
    token = register_and_login(client, "pipeline1@example.com", "secret")
    student_id = create_student(client, token)

    today = datetime(2030, 6, 1, tzinfo=timezone.utc)

    # Draft
    create_session(client, token, student_id, 50.0, 60)
    inv_draft = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_draft["id"], status="draft", due_date=today + timedelta(days=10), balance=Decimal("50.00"))

    # Issued (unpaid)
    create_session(client, token, student_id, 60.0, 60)
    inv_issued = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_issued["id"], status="issued", due_date=today + timedelta(days=5), balance=Decimal("60.00"))

    # Partially paid
    create_session(client, token, student_id, 70.0, 60)
    inv_partial = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_partial["id"], status="partial", due_date=today + timedelta(days=2), balance=Decimal("30.00"))

    # Paid
    create_session(client, token, student_id, 80.0, 60)
    inv_paid = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_paid["id"], status="paid", due_date=today - timedelta(days=1), balance=Decimal("0.00"))

    # Void
    create_session(client, token, student_id, 90.0, 60)
    inv_void = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_void["id"], status="void", due_date=today - timedelta(days=2), balance=Decimal("0.00"))

    resp = client.get(
        "/admin/reports/invoice-pipeline",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    statuses = data["statuses"]
    assert statuses["draft"]["count"] == 1
    assert statuses["issued"]["count"] == 1
    assert statuses["partially_paid"]["count"] == 1
    assert statuses["paid"]["count"] == 1
    assert statuses["void"]["count"] == 1
    assert data["summary"]["invoice_count"] == 4  # void excluded
    assert data["summary"]["total_outstanding"] == "140.00"  # 50 + 60 + 30


def test_invoice_pipeline_due_windows():
    client = TestClient(app)
    token = register_and_login(client, "pipeline2@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 1, tzinfo=timezone.utc)

    # Past due
    create_session(client, token, student_id, 50.0, 60)
    inv_past = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_past["id"], status="issued", due_date=today - timedelta(days=3), balance=Decimal("50.00"))

    # Due next 7
    create_session(client, token, student_id, 60.0, 60)
    inv_week = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_week["id"], status="issued", due_date=today + timedelta(days=5), balance=Decimal("60.00"))

    # Due next 30
    create_session(client, token, student_id, 70.0, 60)
    inv_month = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_month["id"], status="issued", due_date=today + timedelta(days=15), balance=Decimal("70.00"))

    # Beyond 30
    create_session(client, token, student_id, 80.0, 60)
    inv_future = generate_invoice(client, token, student_id)
    set_invoice_fields(inv_future["id"], status="issued", due_date=today + timedelta(days=40), balance=Decimal("80.00"))

    resp = client.get(
        "/admin/reports/invoice-pipeline",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    windows = data["due_windows"]
    assert windows["past_due"]["total_outstanding"] == "50.00"
    assert windows["due_next_7_days"]["total_outstanding"] == "60.00"
    assert windows["due_next_30_days"]["total_outstanding"] == "70.00"


def test_invoice_pipeline_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "pipeline3a@example.com", "secret")
    token_b = register_and_login(client, "pipeline3b@example.com", "secret")
    today = datetime(2030, 6, 1, tzinfo=timezone.utc)

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 50.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)
    set_invoice_fields(inv_a["id"], status="issued", due_date=today + timedelta(days=2), balance=Decimal("50.00"))

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 60.0, 60)
    inv_b = generate_invoice(client, token_b, student_b)
    set_invoice_fields(inv_b["id"], status="issued", due_date=today + timedelta(days=9), balance=Decimal("60.00"))

    resp_a = client.get(
        "/admin/reports/invoice-pipeline",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["summary"]["total_outstanding"] == "50.00"

    resp_b = client.get(
        "/admin/reports/invoice-pipeline",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["summary"]["total_outstanding"] == "60.00"


def test_invoice_pipeline_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "pipeline4@example.com", "secret")

    resp = client.get("/admin/reports/invoice-pipeline", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["invoice_count"] == 0
    assert data["summary"]["total_outstanding"] == "0.00"
    for status_data in data["statuses"].values():
        assert status_data["count"] == 0
        assert status_data["total_outstanding"] == "0.00"
    for win in data["due_windows"].values():
        assert win["count"] == 0
        assert win["total_outstanding"] == "0.00"
