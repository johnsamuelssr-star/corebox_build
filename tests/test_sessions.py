import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.main import app

DEFAULT_START_TIME = "10:00:00"


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


def create_student(client: TestClient, token: str, payload: dict):
    return client.post("/students", json=payload, headers={"Authorization": f"Bearer {token}"})


def test_create_session_for_student_basic():
    client = TestClient(app)
    token = register_and_login(client, "session1@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
            "rate_per_hour": 80.0,
            "notes": "Algebra",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["subject"] == "Math"
    assert data["duration_minutes"] == 60
    assert data["student_id"] == student_id
    assert data["attendance"] == "present"
    assert data["cost_total"] == 60.0


def test_create_session_rejects_other_users_student():
    client = TestClient(app)
    token_a = register_and_login(client, "session2a@example.com", "secret")
    token_b = register_and_login(client, "session2b@example.com", "secret")

    student_id = create_student(client, token_a, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
            "rate_per_hour": 80.0,
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


def test_list_sessions_for_student_owner_isolated():
    client = TestClient(app)
    token = register_and_login(client, "session3@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]

    for i in range(2):
        client.post(
            "/sessions",
            json={
                "student_id": student_id,
                "subject": f"Sub{i}",
                "duration_minutes": 30,
                "session_date": f"2030-01-0{i+1}T10:00:00Z",
                "start_time": DEFAULT_START_TIME,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = client.get(f"/sessions", params={"student_id": student_id}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(sess["student_id"] == student_id for sess in data)

    # isolation
    token_other = register_and_login(client, "session3b@example.com", "secret")
    other_student = create_student(client, token_other, {"parent_name": "P", "student_name": "S"}).json()["id"]
    client.post(
        "/sessions",
        json={
            "student_id": other_student,
            "subject": "Other",
            "duration_minutes": 45,
            "session_date": "2030-01-05T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token_other}"},
    )

    resp_iso = client.get(f"/sessions", params={"student_id": student_id}, headers={"Authorization": f"Bearer {token}"})
    assert resp_iso.status_code == 200
    assert len(resp_iso.json()) == 2


def test_get_session_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "session4a@example.com", "secret")
    token_b = register_and_login(client, "session4b@example.com", "secret")

    student_id = create_student(client, token_a, {"parent_name": "P", "student_name": "S"}).json()["id"]
    session_resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    session_id = session_resp.json()["id"]

    resp = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_update_session_recalculates_cost():
    client = TestClient(app)
    token = register_and_login(client, "session5@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]
    session_resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
            "rate_per_hour": 80.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = session_resp.json()["id"]

    update_resp = client.put(
        f"/sessions/{session_id}",
        json={"duration_minutes": 90},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["cost_total"] == 120.0


def test_delete_session():
    client = TestClient(app)
    token = register_and_login(client, "session6@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]
    session_id = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    delete_resp = client.delete(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    follow_resp = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert follow_resp.status_code == 404


def test_list_sessions_without_student_id_returns_all_user_sessions():
    client = TestClient(app)
    token = register_and_login(client, "session7@example.com", "secret")
    student_a = create_student(client, token, {"parent_name": "A", "student_name": "A"}).json()["id"]
    student_b = create_student(client, token, {"parent_name": "B", "student_name": "B"}).json()["id"]

    client.post(
        "/sessions",
        json={
            "student_id": student_a,
            "subject": "SubA",
            "duration_minutes": 30,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/sessions",
        json={
            "student_id": student_b,
            "subject": "SubB",
            "duration_minutes": 45,
            "session_date": "2030-01-02T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert {sess["subject"] for sess in data} == {"SubA", "SubB"}


def test_create_session_defaults_attendance_and_billing():
    client = TestClient(app)
    token = register_and_login(client, "session8@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "P", "student_name": "S"}).json()["id"]

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["attendance_status"] == "scheduled"
    assert data["billing_status"] == "not_applicable"
    assert data["is_billable"] is True


def test_update_session_attendance_status():
    client = TestClient(app)
    token = register_and_login(client, "session9@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "P", "student_name": "S"}).json()["id"]
    session_id = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    resp = client.put(
        f"/sessions/{session_id}",
        json={"attendance_status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["attendance_status"] == "completed"


def test_update_session_billing_status_and_is_billable():
    client = TestClient(app)
    token = register_and_login(client, "session10@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "P", "student_name": "S"}).json()["id"]
    session_id = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    resp = client.put(
        f"/sessions/{session_id}",
        json={"billing_status": "pending", "is_billable": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["billing_status"] == "pending"
    assert data["is_billable"] is True


def test_invalid_attendance_status_rejected():
    client = TestClient(app)
    token = register_and_login(client, "session11@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "P", "student_name": "S"}).json()["id"]

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
            "attendance_status": "teleported",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_invalid_billing_status_rejected():
    client = TestClient(app)
    token = register_and_login(client, "session12@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "P", "student_name": "S"}).json()["id"]

    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": DEFAULT_START_TIME,
            "billing_status": "unicorn_paid",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_list_sessions_includes_session_date_field():
    client = TestClient(app)
    token = register_and_login(client, "sessiondate@example.com", "secret")
    student_id = create_student(client, token, {"parent_name": "Parent", "student_name": "Student"}).json()["id"]

    target_date = "2025-12-02T09:30:00Z"
    client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": target_date,
            "start_time": DEFAULT_START_TIME,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(sess["session_date"].startswith("2025-12-02") for sess in data)
