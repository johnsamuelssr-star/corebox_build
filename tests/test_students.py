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


def test_create_student_basic():
    client = TestClient(app)
    token = register_and_login(client, "student1@example.com", "secret")
    payload = {"parent_name": "Parent", "student_name": "Student", "grade_level": 5}
    resp = client.post("/students", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["parent_name"] == "Parent"
    assert data["student_name"] == "Student"
    assert data["status"] == "active"


def test_create_student_from_lead():
    client = TestClient(app)
    token = register_and_login(client, "student2@example.com", "secret")
    lead_resp = create_lead(
        client,
        token,
        {"parent_name": "Parent", "student_name": "Student", "grade_level": 4, "status": "new", "notes": None},
    )
    lead_id = lead_resp.json()["id"]

    resp = client.post(
        "/students",
        json={"parent_name": "Parent", "student_name": "Student", "grade_level": 4, "lead_id": lead_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["lead_id"] == lead_id


def test_create_student_rejects_other_users_lead():
    client = TestClient(app)
    token_a = register_and_login(client, "student3a@example.com", "secret")
    token_b = register_and_login(client, "student3b@example.com", "secret")

    lead_resp = create_lead(
        client,
        token_a,
        {"parent_name": "Parent", "student_name": "Student", "grade_level": 4, "status": "new", "notes": None},
    )
    lead_id = lead_resp.json()["id"]

    resp = client.post(
        "/students",
        json={"parent_name": "Other", "student_name": "Other", "lead_id": lead_id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


def test_list_students_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "student4a@example.com", "secret")
    token_b = register_and_login(client, "student4b@example.com", "secret")

    client.post("/students", json={"parent_name": "A1", "student_name": "A1"}, headers={"Authorization": f"Bearer {token_a}"})
    client.post("/students", json={"parent_name": "A2", "student_name": "A2"}, headers={"Authorization": f"Bearer {token_a}"})
    client.post("/students", json={"parent_name": "B1", "student_name": "B1"}, headers={"Authorization": f"Bearer {token_b}"})

    resp = client.get("/students", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(student["parent_name"].startswith("A") for student in data)


def test_list_students_empty_returns_200():
    client = TestClient(app)
    token = register_and_login(client, "student_empty@example.com", "secret")
    resp = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_students_does_not_require_lead():
    client = TestClient(app)
    token = register_and_login(client, "student_nolead@example.com", "secret")

    create_resp = client.post(
        "/students",
        json={"parent_name": "Parent", "student_name": "Student", "grade_level": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code in (200, 201)

    list_resp = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) >= 1
    assert any(student["student_name"] == "Student" for student in data)


def test_get_student_by_id_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "student5a@example.com", "secret")
    token_b = register_and_login(client, "student5b@example.com", "secret")

    create_resp = client.post(
        "/students",
        json={"parent_name": "A1", "student_name": "A1"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    student_id = create_resp.json()["id"]

    resp = client.get(f"/students/{student_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_update_student():
    client = TestClient(app)
    token = register_and_login(client, "student6@example.com", "secret")
    create_resp = client.post(
        "/students",
        json={"parent_name": "Old", "student_name": "Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/students/{student_id}",
        json={"parent_name": "New", "subject_focus": "Math"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["parent_name"] == "New"
    assert data["subject_focus"] == "Math"


def test_delete_student():
    client = TestClient(app)
    token = register_and_login(client, "student7@example.com", "secret")
    create_resp = client.post(
        "/students",
        json={"parent_name": "Delete", "student_name": "Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    follow_resp = client.get(f"/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert follow_resp.status_code == 404
