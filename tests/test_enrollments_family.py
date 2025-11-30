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


def test_family_enrollment_does_not_require_parent_password():
    client = TestClient(app)
    token = register_and_login(client, "family1@example.com", "secret")

    payload = {
        "parent": {
            "first_name": "Test",
            "last_name": "Parent",
            "email": "testparent@example.com",
            "phone": "5551234567",
            "notes": "from test",
        },
        "students": [
            {
                "parent_name": "Test Parent",
                "student_name": "Test Student",
                "grade_level": 5,
                "subject_focus": "Math",
            }
        ],
    }

    resp = client.post("/enrollments/family", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["parent"]["email"] == payload["parent"]["email"]
    assert data["parent"].get("id") is not None
    assert len(data["students"]) == 1
    assert data["students"][0]["student_name"] == "Test Student"
