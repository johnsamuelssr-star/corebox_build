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


def test_owner_students_requires_auth():
    client = TestClient(app)
    response = client.get("/owner/students")
    assert response.status_code in (401, 403)


def test_owner_students_empty_list():
    client = TestClient(app)
    token = register_and_login(client, "ownerstudents_empty@example.com", "secret")
    response = client.get("/owner/students", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_owner_students_returns_data():
    client = TestClient(app)
    token = register_and_login(client, "ownerstudents_data@example.com", "secret")

    create_response = client.post(
        "/students",
        json={
            "parent_name": "Parent Example",
            "student_name": "Alice Doe",
            "grade_level": 6,
            "subject_focus": "Math",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code in (200, 201)

    response = client.get("/owner/students", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    for field in ["id", "firstName", "lastName", "status", "gradeLevel", "subjectFocus", "parentName"]:
        assert field in first
    assert first["status"] in ["active", "inactive"]
    assert first["firstName"] != ""
    assert first["gradeLevel"] == "6"
    assert first["subjectFocus"] == "Math"
