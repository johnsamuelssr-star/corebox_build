from datetime import datetime, timedelta, timezone

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


def test_parent_report_narrative_basic():
    client = TestClient(app)
    token = register_and_login(client, "parentn1@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 100.0, 60, "2030-06-01T10:00:00Z")
    create_session(client, token, student_id, 80.0, 90, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    create_payment(client, token, inv["id"], "120.00")
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/narrative",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "narrative" in data
    narrative = data["narrative"]
    assert all(key in narrative for key in ["overview", "attendance", "academic_progress", "behavior_and_engagement", "next_steps", "billing_overview"])
    assert "2 session" in narrative["overview"]
    assert "Total billed to date" in narrative["billing_overview"]


def test_parent_report_narrative_attendance_tiers():
    client = TestClient(app)
    token = register_and_login(client, "parentn2@example.com", "secret")
    student_id = create_student(client, token)
    base = datetime(2030, 6, 15, tzinfo=timezone.utc)

    # Only two weeks with sessions -> low consistency
    for offset in [0, 4]:
        sess_date = base - timedelta(weeks=offset)
        create_session(client, token, student_id, 50.0, 60, sess_date.isoformat())

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/narrative",
        params={"today": base.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    attn = resp.json()["narrative"]["attendance"]
    assert "inconsistent" in attn


def test_parent_report_narrative_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "parentn3@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/narrative",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "has not started any sessions yet" in data["narrative"]["overview"]
    assert "no sessions in the selected period" in data["narrative"]["academic_progress"]
    assert "0.00" in data["narrative"]["billing_overview"]


def test_parent_report_narrative_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "parentn4a@example.com", "secret")
    token_b = register_and_login(client, "parentn4b@example.com", "secret")

    student_a = create_student(client, token_a)
    student_b = create_student(client, token_b)

    resp = client.get(
        f"/admin/reports/parent-report/{student_b}/narrative",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404

    resp_b = client.get(
        f"/admin/reports/parent-report/{student_b}/narrative",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
