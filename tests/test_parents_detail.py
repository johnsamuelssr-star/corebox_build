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


def create_family_enrollment(client: TestClient, token: str, parent_email: str, student_name: str):
    payload = {
        "parent": {
            "first_name": "Parent",
            "last_name": "One",
            "email": parent_email,
            "phone": "555-0001",
            "notes": "note",
        },
        "students": [
            {"parent_name": "Parent One", "student_name": student_name, "grade_level": 4},
        ],
    }
    resp = client.post("/enrollments/family", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def test_get_parent_detail_and_students():
    client = TestClient(app)
    token = register_and_login(client, "owner@example.com", "secret")
    enrollment = create_family_enrollment(client, token, "parent1@example.com", "Student One")
    parent_id = enrollment["parent"]["id"]

    detail_resp = client.get(f"/parents/{parent_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["email"] == "parent1@example.com"

    students_resp = client.get(f"/parents/{parent_id}/students", headers={"Authorization": f"Bearer {token}"})
    assert students_resp.status_code == 200
    students = students_resp.json()
    assert len(students) == 1
    assert students[0]["id"] == enrollment["students"][0]["id"]


def test_parent_detail_is_owner_scoped():
    client = TestClient(app)
    token_a = register_and_login(client, "ownerA@example.com", "secret")
    token_b = register_and_login(client, "ownerB@example.com", "secret")

    enrollment_a = create_family_enrollment(client, token_a, "parentA@example.com", "Student A")
    parent_a_id = enrollment_a["parent"]["id"]

    resp = client.get(f"/parents/{parent_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
