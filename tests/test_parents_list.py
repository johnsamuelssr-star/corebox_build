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


def test_list_parents_after_family_enrollment():
    client = TestClient(app)
    token = register_and_login(client, "parents1@example.com", "secret")

    payload = {
        "parent": {
            "first_name": "Parent",
            "last_name": "One",
            "email": "parent1@example.com",
            "phone": "555-0001",
            "notes": "note",
        },
        "students": [
            {"parent_name": "Parent One", "student_name": "Student One", "grade_level": 4},
        ],
    }
    enroll_resp = client.post(
        "/enrollments/family",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enroll_resp.status_code in (200, 201)

    list_resp = client.get("/parents", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)
    assert any(item["email"] == "parent1@example.com" for item in data)
