import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.student import Student


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


def create_student(client: TestClient, token: str, parent_name="Parent", student_name="Student") -> int:
    resp = client.post(
        "/students",
        json={"parent_name": parent_name, "student_name": student_name, "grade_level": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_remove_student_soft_deletes_and_anonymizes():
    client = TestClient(app)
    token = register_and_login(client, "owner@example.com", "secret")
    student_id = create_student(client, token)

    resp = client.delete(f"/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    db = SessionLocal()
    student = db.query(Student).filter(Student.id == student_id).first()
    assert student is not None
    assert student.is_active is False
    assert student.is_anonymized is True
    assert student.anonymized_at is not None
    assert student.parent_name in (None, "Deleted Guardian")
    assert student.student_name in (None, "Deleted Student")
    db.close()


def test_removed_student_not_in_list():
    client = TestClient(app)
    token = register_and_login(client, "owner2@example.com", "secret")
    student_id = create_student(client, token)

    del_resp = client.delete(f"/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 200

    list_resp = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert student_id not in ids


def test_remove_student_wrong_owner_404():
    client = TestClient(app)
    token_a = register_and_login(client, "owner3@example.com", "secret")
    token_b = register_and_login(client, "owner4@example.com", "secret")
    student_id = create_student(client, token_a)

    resp = client.delete(f"/students/{student_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
