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


def create_lead(client: TestClient, token: str):
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 1,
        "status": "new",
        "notes": None,
    }
    resp = client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()["id"]


def create_reminder(client: TestClient, token: str, lead_id: int, title: str, due_at: str | None = None):
    body = {"title": title}
    if due_at:
        body["due_at"] = due_at
    return client.post(f"/reminders/leads/{lead_id}/reminders", json=body, headers={"Authorization": f"Bearer {token}"})


def test_create_reminder_for_lead():
    client = TestClient(app)
    token = register_and_login(client, "reminder1@example.com", "secret")
    lead_id = create_lead(client, token)
    resp = create_reminder(client, token, lead_id, "Call back")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Call back"
    assert data["lead_id"] == lead_id


def test_list_reminders_for_lead():
    client = TestClient(app)
    token = register_and_login(client, "reminder2@example.com", "secret")
    lead_id = create_lead(client, token)
    create_reminder(client, token, lead_id, "First")
    create_reminder(client, token, lead_id, "Second")

    resp = client.get(f"/reminders/leads/{lead_id}/reminders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = [r["title"] for r in data]
    assert titles == ["First", "Second"]


def test_cannot_create_reminder_for_other_users_lead():
    client = TestClient(app)
    token_a = register_and_login(client, "remindera@example.com", "secret")
    token_b = register_and_login(client, "reminderb@example.com", "secret")
    lead_id = create_lead(client, token_a)

    resp = create_reminder(client, token_b, lead_id, "Should fail")
    assert resp.status_code == 404


def test_update_reminder_title_and_due_date():
    client = TestClient(app)
    token = register_and_login(client, "reminder3@example.com", "secret")
    lead_id = create_lead(client, token)
    reminder_resp = create_reminder(client, token, lead_id, "Old title")
    reminder_id = reminder_resp.json()["id"]

    update_resp = client.put(
        f"/reminders/{reminder_id}",
        json={"title": "New title", "due_at": "2030-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["title"] == "New title"
    assert data["due_at"] == "2030-01-01T00:00:00+00:00"


def test_mark_reminder_completed_sets_completed_at_and_logs_timeline():
    client = TestClient(app)
    token = register_and_login(client, "reminder4@example.com", "secret")
    lead_id = create_lead(client, token)
    reminder_id = create_reminder(client, token, lead_id, "Complete me").json()["id"]

    resp = client.put(
        f"/reminders/{reminder_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    assert data["completed_at"] is not None

    timeline_resp = client.get(f"/leads/{lead_id}/timeline", headers={"Authorization": f"Bearer {token}"})
    types = [e["event_type"] for e in timeline_resp.json()]
    assert "reminder_completed" in types


def test_uncomplete_reminder_clears_completed_at():
    client = TestClient(app)
    token = register_and_login(client, "reminder5@example.com", "secret")
    lead_id = create_lead(client, token)
    reminder_id = create_reminder(client, token, lead_id, "Toggle me").json()["id"]

    client.put(
        f"/reminders/{reminder_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.put(
        f"/reminders/{reminder_id}",
        json={"completed": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is False
    assert data["completed_at"] is None


def test_delete_reminder():
    client = TestClient(app)
    token = register_and_login(client, "reminder6@example.com", "secret")
    lead_id = create_lead(client, token)
    reminder_id = create_reminder(client, token, lead_id, "Delete me").json()["id"]

    resp = client.delete(f"/reminders/{reminder_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    list_resp = client.get(f"/reminders/leads/{lead_id}/reminders", headers={"Authorization": f"Bearer {token}"})
    ids = [r["id"] for r in list_resp.json()]
    assert reminder_id not in ids


def test_reminders_are_user_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "reminderisolateda@example.com", "secret")
    token_b = register_and_login(client, "reminderisolatedb@example.com", "secret")

    lead_a = create_lead(client, token_a)
    lead_b = create_lead(client, token_b)

    reminder_a = create_reminder(client, token_a, lead_a, "A reminder").json()["id"]
    create_reminder(client, token_b, lead_b, "B reminder")

    resp = client.get(f"/reminders/leads/{lead_a}/reminders", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404

    resp_update = client.put(
        f"/reminders/{reminder_a}",
        json={"title": "Hack"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_update.status_code == 404
