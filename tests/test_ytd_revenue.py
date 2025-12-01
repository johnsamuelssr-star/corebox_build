from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.payment import Payment


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


def set_payment_created_at(payment_id: int, dt: datetime):
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        payment.created_at = dt
        db.commit()
    finally:
        db.close()


def test_ytd_revenue_basic():
    client = TestClient(app)
    token = register_and_login(client, "ytd1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 120.0, 60)
    invoice = generate_invoice(client, token, student_id)
    payment = create_payment(client, token, invoice["id"], "120.00")
    now = datetime.now(timezone.utc)
    set_payment_created_at(payment["id"], datetime(now.year, 1, 15, 12, 0, tzinfo=timezone.utc))

    resp = client.get("/revenue/ytd", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == now.year
    assert data["ytd_revenue"] == "120.00"


def test_ytd_excludes_previous_year():
    client = TestClient(app)
    token = register_and_login(client, "ytd2@example.com", "secret")
    student_id = create_student(client, token)

    create_session(client, token, student_id, 50.0, 60)
    invoice = generate_invoice(client, token, student_id)
    pay_prev = create_payment(client, token, invoice["id"], "50.00")
    # Set to last year
    now = datetime.now(timezone.utc)
    set_payment_created_at(pay_prev["id"], datetime(now.year - 1, 12, 31, 23, 0, tzinfo=timezone.utc))

    create_session(client, token, student_id, 75.0, 60)
    invoice_curr = generate_invoice(client, token, student_id)
    pay_curr = create_payment(client, token, invoice_curr["id"], "75.00")
    set_payment_created_at(pay_curr["id"], datetime(now.year, 2, 1, 12, 0, tzinfo=timezone.utc))

    resp = client.get("/revenue/ytd", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == now.year
    assert data["ytd_revenue"] == "75.00"


def test_ytd_respects_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "ytd3a@example.com", "secret")
    token_b = register_and_login(client, "ytd3b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 60.0, 60)
    invoice_a = generate_invoice(client, token_a, student_a)
    payment_a = create_payment(client, token_a, invoice_a["id"], "60.00")
    now = datetime.now(timezone.utc)
    set_payment_created_at(payment_a["id"], datetime(now.year, 3, 1, 12, 0, tzinfo=timezone.utc))

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 80.0, 60)
    invoice_b = generate_invoice(client, token_b, student_b)
    payment_b = create_payment(client, token_b, invoice_b["id"], "80.00")
    set_payment_created_at(payment_b["id"], datetime(now.year, 3, 2, 12, 0, tzinfo=timezone.utc))

    resp_a = client.get("/revenue/ytd", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["ytd_revenue"] == "60.00"

    resp_b = client.get("/revenue/ytd", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["ytd_revenue"] == "80.00"


def test_ytd_zero_when_no_payments():
    client = TestClient(app)
    token = register_and_login(client, "ytd4@example.com", "secret")

    resp = client.get("/revenue/ytd", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["ytd_revenue"]) == Decimal("0.00")
