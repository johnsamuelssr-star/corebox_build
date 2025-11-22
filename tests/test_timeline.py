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


def create_lead(client: TestClient, token: str, payload: dict):
    return client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})


def get_timeline(client: TestClient, token: str, lead_id: int):
    return client.get(f"/leads/{lead_id}/timeline", headers={"Authorization": f"Bearer {token}"})


def test_timeline_created_on_lead_create():
    client = TestClient(app)
    token = register_and_login(client, "timeline1@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    timeline_resp = get_timeline(client, token, lead_id)
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "lead_created"


def test_timeline_created_on_status_change():
    client = TestClient(app)
    token = register_and_login(client, "timeline2@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    update_resp = client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200

    timeline_resp = get_timeline(client, token, lead_id)
    assert timeline_resp.status_code == 200
    types = [e["event_type"] for e in timeline_resp.json()]
    assert "status_changed" in types


def test_timeline_created_on_note_added():
    client = TestClient(app)
    token = register_and_login(client, "timeline3@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    note_resp = client.post(
        f"/leads/{lead_id}/notes",
        json={"content": "Timeline note"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert note_resp.status_code == 200

    timeline_resp = get_timeline(client, token, lead_id)
    assert timeline_resp.status_code == 200
    types = [e["event_type"] for e in timeline_resp.json()]
    assert "note_added" in types


def test_timeline_field_updates_recorded():
    client = TestClient(app)
    token = register_and_login(client, "timeline4@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    update_resp = client.put(
        f"/leads/{lead_id}",
        json={"parent_name": "New Parent", "grade_level": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200

    timeline_resp = get_timeline(client, token, lead_id)
    descriptions = [e["description"] for e in timeline_resp.json()]
    assert any("Lead updated" in desc for desc in descriptions)


def test_timeline_entries_ordered():
    client = TestClient(app)
    token = register_and_login(client, "timeline5@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/leads/{lead_id}/notes",
        json={"content": "Another note"},
        headers={"Authorization": f"Bearer {token}"},
    )

    timeline_resp = get_timeline(client, token, lead_id)
    events = timeline_resp.json()
    assert timeline_resp.status_code == 200
    assert events == sorted(events, key=lambda e: (e["created_at"], e["id"]))


def test_timeline_user_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "timelinea@example.com", "secret")
    token_b = register_and_login(client, "timelineb@example.com", "secret")
    lead_id = create_lead(
        client,
        token_a,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    resp = get_timeline(client, token_b, lead_id)
    assert resp.status_code == 404
