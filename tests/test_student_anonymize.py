import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_student(client: TestClient, token: str) -> int:
    resp = client.post(
        "/students",
        json={"parent_name": "Parent One", "student_name": "Student One", "grade_level": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int) -> int:
    session_date = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": session_date,
            "notes": "Sensitive notes",
            "attendance": "present",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_anonymize_student_happy_path():
    client = TestClient(app)
    token = register_and_login(client, "owner@example.com", "secret")

    student_id = create_student(client, token)
    create_session(client, token, student_id)

    invoice_resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert invoice_resp.status_code in (200, 201, 400)  # allow no billable sessions edge

    resp = client.post(f"/students/{student_id}/anonymize", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["already_anonymized"] is False
    student = body["student"]
    assert student["is_anonymized"] is True
    assert student["is_active"] is False
    assert student["status"] == "inactive"
    assert student["student_name"] == "Deleted Student"
    assert student["parent_name"] == "Deleted Guardian"

    sessions_resp = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert sessions_resp.status_code == 200
    for s in sessions_resp.json():
        if s["student_id"] == student_id:
            assert s["notes"] == "Content removed during anonymization"

    invoices_resp = client.get("/invoices", params={"student_id": student_id}, headers={"Authorization": f"Bearer {token}"})
    assert invoices_resp.status_code == 200
    # financial records preserved if any exist
    for inv in invoices_resp.json():
        assert inv["student_id"] == student_id


def test_anonymize_student_idempotent():
    client = TestClient(app)
    token = register_and_login(client, "owner2@example.com", "secret")
    student_id = create_student(client, token)

    first = client.post(f"/students/{student_id}/anonymize", headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200
    assert first.json()["already_anonymized"] is False

    second = client.post(f"/students/{student_id}/anonymize", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    assert second.json()["already_anonymized"] is True


def test_anonymize_student_forbidden_for_other_owner():
    client = TestClient(app)
    token_owner = register_and_login(client, "owner3@example.com", "secret")
    token_other = register_and_login(client, "other@example.com", "secret")

    student_id = create_student(client, token_owner)

    resp = client.post(f"/students/{student_id}/anonymize", headers={"Authorization": f"Bearer {token_other}"})
    assert resp.status_code == 404  # isolated by owner filter


def test_anonymize_student_not_found():
    client = TestClient(app)
    token = register_and_login(client, "owner4@example.com", "secret")

    resp = client.post("/students/9999/anonymize", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
