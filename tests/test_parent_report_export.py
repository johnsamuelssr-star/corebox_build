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


def test_parent_report_export_basic():
    client = TestClient(app)
    token = register_and_login(client, "parentexp1@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 100.0, 60, "2030-06-01T10:00:00Z")
    create_session(client, token, student_id, 80.0, 90, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    create_payment(client, token, inv["id"], "120.00")
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/export/pdf",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "parent_report_" in resp.headers.get("content-disposition", "")
    body = resp.content.decode("utf-8")
    assert "Student: Student" in body
    assert "Total sessions (all time): 2" in body


def test_parent_report_export_zero_state():
    client = TestClient(app)
    token = register_and_login(client, "parentexp2@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/export/pdf",
        params={"today": today.date().isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "has not started any sessions yet" in body
    assert "Outstanding balance: 0.00" in body


def test_parent_report_export_period_filter_labeling():
    client = TestClient(app)
    token = register_and_login(client, "parentexp3@example.com", "secret")
    student_id = create_student(client, token)
    today = datetime(2030, 6, 15, tzinfo=timezone.utc)

    create_session(client, token, student_id, 50.0, 60, "2030-05-01T10:00:00Z")
    create_session(client, token, student_id, 70.0, 60, "2030-06-10T10:00:00Z")
    inv = generate_invoice(client, token, student_id)
    set_invoice_created_at(inv["id"], today)

    resp = client.get(
        f"/admin/reports/parent-report/{student_id}/export/pdf",
        params={"today": today.date().isoformat(), "start_date": "2030-06-01", "end_date": "2030-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Period: 2030-06-01 to 2030-06-30" in body
    assert "Sessions this period: 1" in body
    assert "Hours this period: 1.00" in body


def test_parent_report_export_owner_isolation():
    client = TestClient(app)

    # Owner A
    token_a = register_and_login(client, "export_owner_a@example.com", "secret")
    student_a = create_student(client, token_a)

    # Owner B
    token_b = register_and_login(client, "export_owner_b@example.com", "secret")
    student_b = create_student(client, token_b)

    # Owner A attempts to export B's report -> expect forbidden (403 or 404)
    resp_a_for_b = client.get(
        f"/admin/reports/parent-report/{student_b}/export/pdf",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a_for_b.status_code in (403, 404)

    # Owner B CAN export their own student report
    resp_b_for_b = client.get(
        f"/admin/reports/parent-report/{student_b}/export/pdf",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b_for_b.status_code == 200
    assert resp_b_for_b.headers["content-type"].startswith("application/pdf")
