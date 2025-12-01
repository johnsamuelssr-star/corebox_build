from datetime import datetime, timedelta, timezone
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


def create_payment(client: TestClient, token: str, invoice_id: int, amount: str, method: str | None = None):
    payload = {"invoice_id": invoice_id, "amount": amount}
    if method:
        payload["method"] = method
    resp = client.post(
        f"/invoices/{invoice_id}/payments",
        json=payload,
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


def test_payment_analytics_basic_summary():
    client = TestClient(app)
    token = register_and_login(client, "payanalytics1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 50.0, 60)
    inv = generate_invoice(client, token, student_id)

    today = datetime(2030, 6, 15, tzinfo=timezone.utc)
    pay1 = create_payment(client, token, inv["id"], "100.00")
    set_payment_created_at(pay1["id"], today - timedelta(days=2))
    pay2 = create_payment(client, token, inv["id"], "50.00")
    set_payment_created_at(pay2["id"], today - timedelta(days=10))

    resp = client.get(
        "/admin/reports/payment-analytics",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    summary = data["summary"]
    assert summary["total_paid_all_time"] == "150.00"
    assert summary["payment_count_all_time"] == 2
    assert summary["total_paid_last_7_days"] == "100.00"
    assert summary["total_paid_last_30_days"] == "150.00"
    assert summary["average_payment_amount_all_time"] == "75.00"


def test_payment_analytics_weekly_trend_last_8_weeks():
    client = TestClient(app)
    token = register_and_login(client, "payanalytics2@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 50.0, 60)
    inv = generate_invoice(client, token, student_id)

    # Build payments across 8 weeks
    base_today = datetime(2030, 6, 15, tzinfo=timezone.utc).date()
    for i in range(8):
        pay = create_payment(client, token, inv["id"], "10.00")
        set_payment_created_at(pay["id"], datetime.combine(base_today - timedelta(weeks=i), datetime.min.time(), tzinfo=timezone.utc))

    resp = client.get(
        "/admin/reports/payment-analytics",
        params={"today": base_today.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    weekly = data["weekly_trend"]
    assert len(weekly) == 8
    # Oldest week should have one payment of 10.00, newest week also 10.00
    assert weekly[0]["total_paid"] == "10.00"
    assert weekly[-1]["total_paid"] == "10.00"


def test_payment_analytics_monthly_trend_last_12_months():
    client = TestClient(app)
    token = register_and_login(client, "payanalytics3@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 50.0, 60)
    inv = generate_invoice(client, token, student_id)

    base_today = datetime(2030, 6, 15, tzinfo=timezone.utc).date()
    # Payments over several months
    months_offsets = [0, 1, 3, 11]
    for offset in months_offsets:
        pay = create_payment(client, token, inv["id"], "20.00")
        # Set payment at middle of the target month
        month_date = base_today - timedelta(days=30 * offset)
        set_payment_created_at(pay["id"], datetime.combine(month_date.replace(day=15), datetime.min.time(), tzinfo=timezone.utc))

    resp = client.get(
        "/admin/reports/payment-analytics",
        params={"today": base_today.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    monthly = resp.json()["monthly_trend"]
    assert len(monthly) == 12
    # Check the most recent month shows 20.00
    assert monthly[-1]["total_paid"] == "20.00"


def test_payment_analytics_methods_breakdown():
    client = TestClient(app)
    token = register_and_login(client, "payanalytics4@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 50.0, 60)
    inv = generate_invoice(client, token, student_id)

    pay_card = create_payment(client, token, inv["id"], "30.00", method="card")
    set_payment_created_at(pay_card["id"], datetime(2030, 6, 10, tzinfo=timezone.utc))
    pay_cash = create_payment(client, token, inv["id"], "20.00", method="cash")
    set_payment_created_at(pay_cash["id"], datetime(2030, 6, 11, tzinfo=timezone.utc))

    resp = client.get(
        "/admin/reports/payment-analytics",
        params={"today": "2030-06-15"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    methods = resp.json()["methods"]
    methods_map = {m["method"]: m for m in methods}
    assert methods_map["card"]["total_paid"] == "30.00"
    assert methods_map["cash"]["total_paid"] == "20.00"


def test_payment_analytics_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "payanalytics5a@example.com", "secret")
    token_b = register_and_login(client, "payanalytics5b@example.com", "secret")
    student_a = create_student(client, token_a)
    student_b = create_student(client, token_b)
    create_session(client, token_a, student_a, 50.0, 60)
    create_session(client, token_b, student_b, 60.0, 60)
    inv_a = generate_invoice(client, token_a, student_a)
    inv_b = generate_invoice(client, token_b, student_b)
    pay_a = create_payment(client, token_a, inv_a["id"], "40.00")
    pay_b = create_payment(client, token_b, inv_b["id"], "60.00")
    set_payment_created_at(pay_a["id"], datetime(2030, 6, 10, tzinfo=timezone.utc))
    set_payment_created_at(pay_b["id"], datetime(2030, 6, 11, tzinfo=timezone.utc))

    resp_a = client.get(
        "/admin/reports/payment-analytics",
        params={"today": "2030-06-15"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_b = client.get(
        "/admin/reports/payment-analytics",
        params={"today": "2030-06-15"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    data_a = resp_a.json()
    data_b = resp_b.json()
    assert data_a["summary"]["total_paid_all_time"] == "40.00"
    assert data_b["summary"]["total_paid_all_time"] == "60.00"


def test_payment_analytics_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "payanalytics6@example.com", "secret")

    resp = client.get("/admin/reports/payment-analytics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    summary = data["summary"]
    assert summary["total_paid_all_time"] == "0.00"
    assert summary["payment_count_all_time"] == 0
    assert summary["average_payment_amount_all_time"] == "0.00"
    assert len(data["weekly_trend"]) == 8
    assert len(data["monthly_trend"]) == 12
    assert data["methods"] == [] or all(m["total_paid"] == "0.00" for m in data["methods"])
