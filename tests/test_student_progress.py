import pytest
from fastapi.testclient import TestClient

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


def create_student(client: TestClient, token: str, parent_name: str, student_name: str):
    resp = client.post(
        "/students",
        json={"parent_name": parent_name, "student_name": student_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int, subject: str | None, duration: int, rate: float):
    body = {
        "student_id": student_id,
        "subject": subject if subject is not None else "",
        "duration_minutes": duration,
        "session_date": "2030-01-01T10:00:00Z",
        "start_time": "10:00:00",
        "rate_per_hour": rate,
    }
    resp = client.post("/sessions", json=body, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def test_student_progress_basic():
    client = TestClient(app)
    token = register_and_login(client, "progress1@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    create_session(client, token, student_id, "Math", 60, 80.0)
    create_session(client, token, student_id, "Math", 30, 80.0)
    create_session(client, token, student_id, "Reading", 90, 100.0)

    resp = client.get(f"/students/{student_id}/progress", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == student_id
    assert data["total_sessions"] == 3
    assert data["total_minutes"] == 180
    assert data["total_hours"] == 3.0
    assert data["total_earned"] == 270.0
    assert data["average_minutes_per_session"] == pytest.approx(60.0)
    assert data["average_earned_per_session"] == pytest.approx(90.0)

    subjects = {s["subject"]: s for s in data["subjects"]}
    assert len(subjects) == 2
    math = subjects["Math"]
    assert math["sessions_count"] == 2
    assert math["total_minutes"] == 90
    assert math["total_hours"] == 1.5
    assert math["total_earned"] == 120.0
    reading = subjects["Reading"]
    assert reading["sessions_count"] == 1
    assert reading["total_minutes"] == 90
    assert reading["total_hours"] == 1.5
    assert reading["total_earned"] == 150.0


def test_student_progress_no_sessions():
    client = TestClient(app)
    token = register_and_login(client, "progress2@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    resp = client.get(f"/students/{student_id}/progress", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_minutes"] == 0
    assert data["total_hours"] == 0.0
    assert data["total_earned"] == 0.0
    assert data["average_minutes_per_session"] == 0.0
    assert data["average_earned_per_session"] == 0.0
    assert data["subjects"] == []


def test_student_progress_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "progress3a@example.com", "secret")
    token_b = register_and_login(client, "progress3b@example.com", "secret")

    student_id = create_student(client, token_a, "Parent", "Student")
    create_session(client, token_a, student_id, "Math", 60, 80.0)

    resp = client.get(f"/students/{student_id}/progress", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Student not found"


def test_student_progress_handles_missing_subject():
    client = TestClient(app)
    token = register_and_login(client, "progress4@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    create_session(client, token, student_id, None, 30, 50.0)
    create_session(client, token, student_id, "Science", 60, 50.0)

    resp = client.get(f"/students/{student_id}/progress", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    subjects = {s["subject"]: s for s in data["subjects"]}
    assert "Unspecified" in subjects
    assert "Science" in subjects
    assert subjects["Unspecified"]["sessions_count"] == 1
