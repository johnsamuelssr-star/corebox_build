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


def test_parent_report_basic_structure():
    client = TestClient(app)
    token = register_and_login(client, "parent1@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 100.0, 60, "2030-06-01T10:00:00Z")
    create_session(client, token, student_id, 80.0, 90, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    create_payment(client, token, inv["id"], "120.00")
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["as_of"] == today.date().isoformat()
    assert data["period"]["start_date"] is None
    assert data["period"]["end_date"] is None
    assert data["student"]["id"] == student_id
    assert data["progress_summary"]["total_sessions_all_time"] == 2
    assert data["billing_summary"]["total_invoiced_all_time"] == "180.00"
    assert len(data["weekly_activity_last_8_weeks"]) == 8


def test_parent_report_with_period_filter():
    client = TestClient(app)
    token = register_and_login(client, "parent2@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 50.0, 60, "2030-05-01T10:00:00Z")
    create_session(client, token, student_id, 70.0, 60, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}",
        params={"today": today.date().isoformat(), "start_date": "2030-06-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"]["start_date"] == "2030-06-01"
    # Only one session in period
    assert data["progress_summary"]["sessions_in_period"] == 1
    assert data["progress_summary"]["hours_in_period"] == "1.00"


def test_parent_report_uses_student_analytics_values():
    client = TestClient(app)
    token = register_and_login(client, "parent3@example.com", "secret")
    student_id = create_student(client, token)
    base = datetime(2030, 6, 15, tzinfo=timezone.utc)

    week_offsets = [0, 1, 2]
    for offset in week_offsets:
        sess_date = base - timedelta(weeks=offset)
        create_session(client, token, student_id, 60.0, 60, sess_date.isoformat())

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}",
        params={"today": base.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    ps = data["progress_summary"]
    assert ps["consistency_score_0_100"] == data["progress_summary"]["consistency_score_0_100"]
    assert ps["current_session_streak_weeks"] >= 1
    assert len(data["weekly_activity_last_8_weeks"]) == 8


def test_parent_report_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "parent4a@example.com", "secret")
    token_b = register_and_login(client, "parent4b@example.com", "secret")

    student_a = create_student(client, token_a)
    student_b = create_student(client, token_b)

    resp = client.get(
        f"/admin/reports/parent-report/{student_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404

    resp_b = client.get(
        f"/admin/reports/parent-report/{student_b}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200


def test_parent_report_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "parent5@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress_summary"]["total_sessions_all_time"] == 0
    assert data["billing_summary"]["total_invoiced_all_time"] == "0.00"
    assert len(data["weekly_activity_last_8_weeks"]) == 8
