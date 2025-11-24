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


def test_monthly_revenue_single_payment():
    client = TestClient(app)
    token = register_and_login(client, "reportrev1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)
    payment = create_payment(client, token, invoice["id"], "100.00")
    set_payment_created_at(payment["id"], datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc))

    resp = client.get("/reports/monthly-revenue", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["year"] == 2030
    assert data[0]["month"] == 1
    assert data[0]["total_revenue"] == "100.00"


def test_monthly_revenue_multiple_months():
    client = TestClient(app)
    token = register_and_login(client, "reportrev2@example.com", "secret")
    student_id = create_student(client, token)

    create_session(client, token, student_id, 80.0, 60)
    invoice = generate_invoice(client, token, student_id)
    pay1 = create_payment(client, token, invoice["id"], "80.00")
    set_payment_created_at(pay1["id"], datetime(2030, 1, 10, 10, 0, tzinfo=timezone.utc))

    create_session(client, token, student_id, 90.0, 60)
    invoice2 = generate_invoice(client, token, student_id)
    pay2 = create_payment(client, token, invoice2["id"], "90.00")
    set_payment_created_at(pay2["id"], datetime(2030, 2, 5, 10, 0, tzinfo=timezone.utc))

    resp = client.get("/reports/monthly-revenue", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Expect February first (desc), then January
    assert data[0]["month"] == 2
    assert data[0]["total_revenue"] == "90.00"
    assert data[1]["month"] == 1
    assert data[1]["total_revenue"] == "80.00"


def test_monthly_revenue_respects_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "reportrev3a@example.com", "secret")
    token_b = register_and_login(client, "reportrev3b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 70.0, 60)
    invoice_a = generate_invoice(client, token_a, student_a)
    pay_a = create_payment(client, token_a, invoice_a["id"], "70.00")
    set_payment_created_at(pay_a["id"], datetime(2030, 3, 1, 12, 0, tzinfo=timezone.utc))

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 60.0, 60)
    invoice_b = generate_invoice(client, token_b, student_b)
    pay_b = create_payment(client, token_b, invoice_b["id"], "60.00")
    set_payment_created_at(pay_b["id"], datetime(2030, 3, 2, 12, 0, tzinfo=timezone.utc))

    resp = client.get("/reports/monthly-revenue", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["total_revenue"] == "70.00"

    resp_b = client.get("/reports/monthly-revenue", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert len(data_b) == 1
    assert data_b[0]["total_revenue"] == "60.00"


def test_monthly_revenue_date_filters():
    client = TestClient(app)
    token = register_and_login(client, "reportrev4@example.com", "secret")
    student_id = create_student(client, token)

    create_session(client, token, student_id, 50.0, 60)
    invoice = generate_invoice(client, token, student_id)
    pay_jan = create_payment(client, token, invoice["id"], "50.00")
    set_payment_created_at(pay_jan["id"], datetime(2030, 1, 5, 12, 0, tzinfo=timezone.utc))

    create_session(client, token, student_id, 60.0, 60)
    invoice_feb = generate_invoice(client, token, student_id)
    pay_feb = create_payment(client, token, invoice_feb["id"], "60.00")
    set_payment_created_at(pay_feb["id"], datetime(2030, 2, 5, 12, 0, tzinfo=timezone.utc))

    create_session(client, token, student_id, 70.0, 60)
    invoice_mar = generate_invoice(client, token, student_id)
    pay_mar = create_payment(client, token, invoice_mar["id"], "70.00")
    set_payment_created_at(pay_mar["id"], datetime(2030, 3, 5, 12, 0, tzinfo=timezone.utc))

    resp = client.get(
        "/reports/monthly-revenue",
        params={"from_date": "2030-02-01", "to_date": "2030-02-28"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["month"] == 2
    assert data[0]["total_revenue"] == "60.00"
