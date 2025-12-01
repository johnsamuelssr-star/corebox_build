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


def test_owner_can_add_student_to_existing_parent():
    client = TestClient(app)
    token = register_and_login(client, "ownerparentstudent@example.com", "secret")

    parent_resp = client.post(
        "/parents",
        json={"email": "parentadd@example.com", "first_name": "Parent", "last_name": "Add"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert parent_resp.status_code in (200, 201)
    parent_id = parent_resp.json()["id"]

    student_payload = {
        "student_name": "Child One",
        "grade_level": 5,
        "subject_focus": "Math",
        "status": "active",
    }
    add_resp = client.post(
        f"/parents/{parent_id}/students",
        json=student_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert add_resp.status_code in (200, 201)
    student = add_resp.json()
    assert student["student_name"] == student_payload["student_name"]

    list_resp = client.get(f"/parents/{parent_id}/students", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    students = list_resp.json()
    assert any(stu["student_name"] == student_payload["student_name"] for stu in students)


def test_cannot_add_student_to_other_owner_parent():
    client = TestClient(app)
    token_a = register_and_login(client, "ownerA@example.com", "secret")
    token_b = register_and_login(client, "ownerB@example.com", "secret")

    parent_resp = client.post(
        "/parents",
        json={"email": "parentownerA@example.com", "first_name": "Parent", "last_name": "OwnerA"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    parent_id = parent_resp.json()["id"]

    add_resp = client.post(
        f"/parents/{parent_id}/students",
        json={"student_name": "Should Not Work"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert add_resp.status_code == 404
