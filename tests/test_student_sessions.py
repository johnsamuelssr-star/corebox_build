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


def create_session(client: TestClient, token: str, student_id: int, subject: str, duration: int, rate: float = None):
    body = {
        "student_id": student_id,
        "subject": subject,
        "duration_minutes": duration,
        "session_date": "2030-01-01T10:00:00Z",
        "start_time": "10:00:00",
    }
    if rate is not None:
        body["rate_per_hour"] = rate
    resp = client.post("/sessions", json=body, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_student_sessions_lists_only_that_students_sessions():
    client = TestClient(app)
    token = register_and_login(client, "studsess1@example.com", "secret")
    s1 = create_student(client, token, "Parent1", "Student1")
    s2 = create_student(client, token, "Parent2", "Student2")

    create_session(client, token, s1, "Math", 60)
    create_session(client, token, s1, "Science", 45)
    create_session(client, token, s2, "History", 30)

    resp = client.get(f"/students/{s1}/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(sess["student_id"] == s1 for sess in data)


def test_student_sessions_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "studsess2a@example.com", "secret")
    token_b = register_and_login(client, "studsess2b@example.com", "secret")

    s_a = create_student(client, token_a, "ParentA", "StudentA")
    create_session(client, token_a, s_a, "Math", 60)

    s_b = create_student(client, token_b, "ParentB", "StudentB")
    create_session(client, token_b, s_b, "Science", 45)

    resp = client.get(f"/students/{s_a}/sessions", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_student_summary_basic():
    client = TestClient(app)
    token = register_and_login(client, "studsess3@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    create_session(client, token, student_id, "Math", 60, rate=80.0)
    create_session(client, token, student_id, "Science", 90, rate=80.0)

    resp = client.get(f"/students/{student_id}/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == student_id
    assert data["total_sessions"] == 2
    assert data["total_minutes"] == 150
    assert data["total_hours"] == 2.5
    assert data["total_earned"] == 200.0


def test_student_summary_zero_when_no_sessions():
    client = TestClient(app)
    token = register_and_login(client, "studsess4@example.com", "secret")
    student_id = create_student(client, token, "Parent", "Student")

    resp = client.get(f"/students/{student_id}/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_minutes"] == 0
    assert data["total_hours"] == 0.0
    assert data["total_earned"] == 0.0


def test_student_summary_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "studsess5a@example.com", "secret")
    token_b = register_and_login(client, "studsess5b@example.com", "secret")

    student_id = create_student(client, token_a, "Parent", "Student")
    create_session(client, token_a, student_id, "Math", 60, rate=80.0)

    resp = client.get(f"/students/{student_id}/summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
