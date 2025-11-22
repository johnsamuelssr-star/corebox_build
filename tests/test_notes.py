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


def create_lead(client: TestClient, token: str, payload: dict):
    return client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})


def test_create_note_for_lead():
    client = TestClient(app)
    token = register_and_login(client, "notes@example.com", "secret")
    lead_resp = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = lead_resp.json()["id"]

    note_resp = client.post(
        f"/leads/{lead_id}/notes",
        json={"content": "First note"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert note_resp.status_code == 200
    data = note_resp.json()
    assert data["content"] == "First note"
    assert data["lead_id"] == lead_id


def test_list_notes_for_lead():
    client = TestClient(app)
    token = register_and_login(client, "listnotes@example.com", "secret")
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

    contents = ["First", "Second", "Third"]
    for c in contents:
        client.post(
            f"/leads/{lead_id}/notes",
            json={"content": c},
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = client.get(f"/leads/{lead_id}/notes", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    returned = [note["content"] for note in resp.json()]
    assert returned == contents


def test_notes_are_user_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "isolatea@example.com", "secret")
    token_b = register_and_login(client, "isolateb@example.com", "secret")

    lead_id = create_lead(
        client,
        token_a,
        {
            "parent_name": "ParentA",
            "student_name": "StudentA",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    client.post(
        f"/leads/{lead_id}/notes",
        json={"content": "Private"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp = client.get(f"/leads/{lead_id}/notes", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_cannot_note_other_users_leads():
    client = TestClient(app)
    token_a = register_and_login(client, "nota@example.com", "secret")
    token_b = register_and_login(client, "notb@example.com", "secret")

    lead_id = create_lead(
        client,
        token_a,
        {
            "parent_name": "ParentA",
            "student_name": "StudentA",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    resp = client.post(
        f"/leads/{lead_id}/notes",
        json={"content": "Should fail"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


def test_validation_requires_content():
    client = TestClient(app)
    token = register_and_login(client, "noval@example.com", "secret")
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

    resp = client.post(
        f"/leads/{lead_id}/notes",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
