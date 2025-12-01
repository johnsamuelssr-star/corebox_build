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
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def create_lead(client: TestClient, token: str, parent_name: str):
    return client.post(
        "/leads",
        json={"parent_name": parent_name, "student_name": "Student", "grade_level": 1, "status": "new", "notes": None},
        headers={"Authorization": f"Bearer {token}"},
    )


def create_student(client: TestClient, token: str, parent_name: str, student_name: str):
    resp = client.post(
        "/students",
        json={"parent_name": parent_name, "student_name": student_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int, subject: str, duration: int, rate: float):
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": subject,
            "duration_minutes": duration,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "rate_per_hour": rate,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def test_dashboard_overview_empty():
    client = TestClient(app)
    token = register_and_login(client, "dash1@example.com", "secret")
    resp = client.get("/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_leads"] == 0
    assert data["total_students"] == 0
    assert data["total_sessions"] == 0
    assert data["total_minutes"] == 0
    assert data["total_hours"] == 0.0
    assert data["total_earned"] == 0.0
    assert data["average_minutes_per_session"] == 0.0
    assert data["average_earned_per_session"] == 0.0
    assert data["subjects"] == []
    assert data["students"] == []


def test_dashboard_overview_basic_aggregation():
    client = TestClient(app)
    token = register_and_login(client, "dash2@example.com", "secret")

    create_lead(client, token, "Lead1")
    create_lead(client, token, "Lead2")

    student_a = create_student(client, token, "ParentA", "StudentA")
    student_b = create_student(client, token, "ParentB", "StudentB")

    create_session(client, token, student_a, "Math", 60, 80.0)
    create_session(client, token, student_a, "Math", 30, 80.0)
    create_session(client, token, student_b, "Reading", 90, 100.0)

    resp = client.get("/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_leads"] == 2
    assert data["total_students"] == 2
    assert data["total_sessions"] == 3
    assert data["total_minutes"] == 180
    assert data["total_hours"] == 3.0
    assert data["total_earned"] == 270.0
    assert data["average_minutes_per_session"] == 60.0
    assert data["average_earned_per_session"] == 90.0

    subjects = {s["subject"]: s for s in data["subjects"]}
    assert len(subjects) == 2
    assert subjects["Math"]["sessions_count"] == 2
    assert subjects["Math"]["total_minutes"] == 90
    assert subjects["Math"]["total_hours"] == 1.5
    assert subjects["Math"]["total_earned"] == 120.0
    assert subjects["Reading"]["sessions_count"] == 1
    assert subjects["Reading"]["total_minutes"] == 90
    assert subjects["Reading"]["total_hours"] == 1.5
    assert subjects["Reading"]["total_earned"] == 150.0

    students = {s["student_name"]: s for s in data["students"]}
    assert len(students) == 2
    assert students["StudentA"]["total_sessions"] == 2
    assert students["StudentA"]["total_minutes"] == 90
    assert students["StudentA"]["total_hours"] == 1.5
    assert students["StudentA"]["total_earned"] == 120.0
    assert students["StudentB"]["total_sessions"] == 1
    assert students["StudentB"]["total_minutes"] == 90
    assert students["StudentB"]["total_hours"] == 1.5
    assert students["StudentB"]["total_earned"] == 150.0


def test_dashboard_overview_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "dash3a@example.com", "secret")
    token_b = register_and_login(client, "dash3b@example.com", "secret")

    student_a = create_student(client, token_a, "ParentA", "StudentA")
    create_session(client, token_a, student_a, "Math", 60, 80.0)

    resp_a = client.get("/dashboard/overview", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total_students"] == 1
    assert data_a["total_sessions"] == 1
    assert data_a["total_earned"] == 80.0

    resp_b = client.get("/dashboard/overview", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total_students"] == 0
    assert data_b["total_sessions"] == 0
    assert data_b["total_earned"] == 0.0
