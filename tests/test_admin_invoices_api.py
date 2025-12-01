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


def create_invoice_for_user(client: TestClient, token: str):
    student_resp = client.post(
        "/students",
        json={"parent_name": "P", "student_name": "S"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = student_resp.json()["id"]
    client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": 60,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "rate_per_hour": 80.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    inv_resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert inv_resp.status_code in (200, 201)
    return inv_resp.json()


def test_admin_can_list_all_invoices():
    client = TestClient(app)
    admin_token = register_and_login(client, "admininv@example.com", "secret")
    user_token = register_and_login(client, "userinv@example.com", "secret")

    inv_admin = create_invoice_for_user(client, admin_token)
    inv_user = create_invoice_for_user(client, user_token)

    resp = client.get("/admin/invoices", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    ids = [inv["id"] for inv in resp.json()]
    assert inv_admin["id"] in ids
    assert inv_user["id"] in ids

    resp_user = client.get("/admin/invoices", headers={"Authorization": f"Bearer {user_token}"})
    assert resp_user.status_code == 403


def test_admin_filter_by_owner_and_status():
    client = TestClient(app)
    admin_token = register_and_login(client, "admininv2@example.com", "secret")
    user_token = register_and_login(client, "userinv2@example.com", "secret")

    inv_admin = create_invoice_for_user(client, admin_token)
    inv_user = create_invoice_for_user(client, user_token)

    resp = client.get(
        "/admin/invoices",
        params={"owner_id": inv_user["owner_id"], "status": inv_user["status"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(inv["owner_id"] == inv_user["owner_id"] for inv in data)


def test_admin_sorting_and_pagination():
    client = TestClient(app)
    admin_token = register_and_login(client, "admininv3@example.com", "secret")

    invoices = []
    for rate in [50.0, 100.0, 75.0]:
        inv = create_invoice_for_user(client, admin_token)
        invoices.append(inv)

    resp = client.get(
        "/admin/invoices",
        params={"sort_by": "total_amount", "sort_order": "asc", "skip": 0, "limit": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
