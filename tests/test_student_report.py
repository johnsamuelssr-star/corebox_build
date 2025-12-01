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


def create_student(client: TestClient, token: str, parent_name: str, student_name: str, grade_level: int | None = None):
    payload = {"parent_name": parent_name, "student_name": student_name}
    if grade_level is not None:
        payload["grade_level"] = grade_level
    resp = client.post("/students", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def create_session(client: TestClient, token: str, student_id: int, subject: str, duration: int, date_str: str, rate: float = None):
    body = {
        "student_id": student_id,
        "subject": subject,
        "duration_minutes": duration,
        "session_date": date_str,
        "start_time": "10:00:00",
    }
    if rate is not None:
        body["rate_per_hour"] = rate
    resp = client.post("/sessions", json=body, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def test_student_report_basic():
    client = TestClient(app)
    token = register_and_login(client, "report1@example.com", "secret")
    student = create_student(client, token, "Parent", "Student", grade_level=5)
    student_id = student["id"]

    create_session(client, token, student_id, "Math", 60, "2030-01-02T10:00:00Z", rate=80.0)
    create_session(client, token, student_id, "Science", 90, "2030-01-03T10:00:00Z", rate=80.0)
    create_session(client, token, student_id, "History", 30, "2030-01-01T10:00:00Z", rate=80.0)

    resp = client.get(f"/students/{student_id}/report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == student_id
    assert data["parent_name"] == "Parent"
    assert data["student_name"] == "Student"
    assert data["grade_level"] == 5
    assert data["total_sessions"] == 3
    assert data["total_minutes"] == 180
    assert data["total_hours"] == 3.0
    assert data["total_earned"] == 240.0
    assert len(data["recent_sessions"]) == 3
    assert data["first_session_date"] <= data["last_session_date"]


def test_student_report_no_sessions():
    client = TestClient(app)
    token = register_and_login(client, "report2@example.com", "secret")
    student = create_student(client, token, "Parent", "Student")
    student_id = student["id"]

    resp = client.get(f"/students/{student_id}/report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_minutes"] == 0
    assert data["total_hours"] == 0.0
    assert data["total_earned"] == 0.0
    assert data["first_session_date"] is None
    assert data["last_session_date"] is None
    assert data["recent_sessions"] == []


def test_student_report_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "report3a@example.com", "secret")
    token_b = register_and_login(client, "report3b@example.com", "secret")

    student = create_student(client, token_a, "Parent", "Student")
    student_id = student["id"]
    create_session(client, token_a, student_id, "Math", 60, "2030-01-01T10:00:00Z")

    resp = client.get(f"/students/{student_id}/report", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Student not found"


def test_student_report_recent_sessions_order():
    client = TestClient(app)
    token = register_and_login(client, "report4@example.com", "secret")
    student = create_student(client, token, "Parent", "Student")
    student_id = student["id"]

    create_session(client, token, student_id, "Day1", 30, "2030-01-01T10:00:00Z")
    create_session(client, token, student_id, "Day3", 30, "2030-01-03T10:00:00Z")
    create_session(client, token, student_id, "Day2", 30, "2030-01-02T10:00:00Z")

    resp = client.get(f"/students/{student_id}/report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    subjects = [s["subject"] for s in data["recent_sessions"]]
    assert subjects == ["Day3", "Day2", "Day1"]
