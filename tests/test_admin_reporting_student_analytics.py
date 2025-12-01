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


def test_student_analytics_basic_kpis():
    client = TestClient(app)
    token = register_and_login(client, "studana1@example.com", "secret")
    student_id = create_student(client, token)

    today = datetime(2030, 6, 15, tzinfo=timezone.utc)
    s1 = create_session(client, token, student_id, 100.0, 60, "2030-06-01T10:00:00Z")
    s2 = create_session(client, token, student_id, 80.0, 90, "2030-06-10T10:00:00Z")

    inv = generate_invoice(client, token, student_id)
    create_payment(client, token, inv["id"], "120.00")
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        "/admin/reports/student-analytics",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["students"]) == 1
    kpis = data["students"][0]["kpis"]
    assert kpis["total_sessions"] == 2
    # total hours: 1 + 1.5 = 2.5
    assert kpis["total_hours"] == "2.50"
    assert kpis["total_invoiced"] == "180.00"  # 100 + 80
    assert kpis["total_paid"] == "120.00"
    assert kpis["total_outstanding"] == "60.00"
    assert kpis["last_session_date"] == "2030-06-10"
    assert kpis["first_session_date"] == "2030-06-01"
    # billing vs usage ratio: 180 / 2.5 = 72
    assert kpis["billing_vs_usage_ratio"] == "72.00"


def test_student_analytics_weekly_trend_and_consistency():
    client = TestClient(app)
    token = register_and_login(client, "studana2@example.com", "secret")
    student_id = create_student(client, token)
    base = datetime(2030, 6, 15, tzinfo=timezone.utc)

    # Create sessions in weeks: newest weeks have sessions in first 3 weeks, then a gap, then one earlier
    week_offsets = [0, 1, 2, 5]
    for offset in week_offsets:
        sess_date = base - timedelta(weeks=offset)
        create_session(client, token, student_id, 60.0, 60, (sess_date.isoformat()))

    resp = client.get(
        "/admin/reports/student-analytics",
        params={"today": base.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    student = data["students"][0]
    weekly = student["weekly_activity_last_8_weeks"]
    assert len(weekly) == 8
    sessions_last_8 = student["kpis"]["sessions_last_8_weeks"]
    assert sessions_last_8 == len(week_offsets)
    weeks_with_sessions = sum(1 for w in weekly if w["session_count"] > 0)
    assert student["kpis"]["consistency_score_0_100"] == round(100 * weeks_with_sessions / 8)
    # streak should be at least 3 given sessions in weeks 0,1,2 and a gap afterwards
    assert student["kpis"]["current_session_streak_weeks"] == 3


def test_student_analytics_multiple_students():
    client = TestClient(app)
    token = register_and_login(client, "studana3@example.com", "secret")
    student_a = create_student(client, token)
    student_b = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_a, 60.0, 60, "2030-06-01T10:00:00Z")
    inv_a = generate_invoice(client, token, student_a)
    create_payment(client, token, inv_a["id"], "60.00")

    create_session(client, token, student_b, 80.0, 60, "2030-06-02T10:00:00Z")
    inv_b = generate_invoice(client, token, student_b)

    resp = client.get(
        "/admin/reports/student-analytics",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["students"]) == 2
    # Ensure totals per student are independent
    stu_map = {s["student_id"]: s for s in data["students"]}
    assert stu_map[student_a]["kpis"]["total_paid"] == "60.00"
    assert stu_map[student_b]["kpis"]["total_paid"] == "0.00"


def test_student_analytics_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "studana4a@example.com", "secret")
    token_b = register_and_login(client, "studana4b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 50.0, 60, "2030-06-01T10:00:00Z")
    inv_a = generate_invoice(client, token_a, student_a)
    create_payment(client, token_a, inv_a["id"], "50.00")

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 70.0, 60, "2030-06-02T10:00:00Z")

    resp_a = client.get("/admin/reports/student-analytics", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/admin/reports/student-analytics", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    data_a = resp_a.json()
    data_b = resp_b.json()
    assert all(s["student_id"] == student_a for s in data_a["students"])
    assert all(s["student_id"] == student_b for s in data_b["students"])


def test_student_analytics_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "studana5@example.com", "secret")
    # No students yet
    resp = client.get("/admin/reports/student-analytics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["students"] == []
