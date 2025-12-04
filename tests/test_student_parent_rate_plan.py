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


def create_parent(client: TestClient, token: str, email: str, rate_plan: str):
    resp = client.post(
        "/parents",
        json={"email": email, "first_name": "Parent", "last_name": "Plan", "rate_plan": rate_plan},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def add_student(client: TestClient, token: str, parent_id: int, name: str):
    resp = client.post(
        f"/parents/{parent_id}/students",
        json={"student_name": name, "grade_level": 4},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def test_students_include_parent_id_and_rate_plan():
    client = TestClient(app)
    token = register_and_login(client, "owner@example.com", "secret")

    parent_regular = create_parent(client, token, "reg@example.com", "regular")
    parent_discount = create_parent(client, token, "disc@example.com", "discount")

    stu_reg = add_student(client, token, parent_regular["id"], "Reg Student")
    stu_disc = add_student(client, token, parent_discount["id"], "Disc Student")

    # Detail
    detail_reg = client.get(f"/students/{stu_reg['id']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail_reg["parent_id"] == parent_regular["id"]
    assert detail_reg["parent_rate_plan"] == "regular"

    detail_disc = client.get(f"/students/{stu_disc['id']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail_disc["parent_id"] == parent_discount["id"]
    assert detail_disc["parent_rate_plan"] == "discount"

    # List
    list_resp = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    reg_item = next(s for s in data if s["id"] == stu_reg["id"])
    disc_item = next(s for s in data if s["id"] == stu_disc["id"])
    assert reg_item["parent_id"] == parent_regular["id"]
    assert reg_item["parent_rate_plan"] == "regular"
    assert disc_item["parent_id"] == parent_discount["id"]
    assert disc_item["parent_rate_plan"] == "discount"
