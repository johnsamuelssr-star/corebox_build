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


def test_non_admin_cannot_access_admin_endpoints():
    client = TestClient(app)
    register_and_login(client, "admin1@example.com", "secret")  # first user becomes admin
    token_user = register_and_login(client, "user@example.com", "secret")

    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token_user}"})
    assert resp.status_code == 403


def test_first_registered_user_is_admin():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin2@example.com", "secret")

    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["email"] == "admin2@example.com" and u["is_admin"] for u in users)


def test_admin_can_list_users():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin3@example.com", "secret")
    register_and_login(client, "admin3b@example.com", "secret")

    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 2
    emails = [u["email"] for u in users]
    assert "admin3@example.com" in emails
    assert "admin3b@example.com" in emails


def test_admin_can_get_single_user():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin4@example.com", "secret")
    register_and_login(client, "admin4b@example.com", "secret")

    resp_list = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    users = resp_list.json()
    target = next(u for u in users if u["email"] == "admin4b@example.com")

    resp = client.get(f"/admin/users/{target['id']}", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin4b@example.com"


def test_admin_can_deactivate_user_and_login_fails():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin5@example.com", "secret")
    client.post("/auth/register", json={"email": "admin5b@example.com", "password": "secret"})

    resp_list = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    target = next(u for u in resp_list.json() if u["email"] == "admin5b@example.com")

    resp = client.patch(
        f"/admin/users/{target['id']}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login_resp = client.post("/auth/login", json={"email": "admin5b@example.com", "password": "secret"})
    assert login_resp.status_code == 400


def test_admin_cannot_deactivate_self():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin6@example.com", "secret")

    resp_list = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    me = next(u for u in resp_list.json() if u["email"] == "admin6@example.com")

    resp = client.patch(
        f"/admin/users/{me['id']}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 400


def test_admin_can_promote_other_user_to_admin():
    client = TestClient(app)
    token_admin = register_and_login(client, "admin7@example.com", "secret")
    client.post("/auth/register", json={"email": "admin7b@example.com", "password": "secret"})

    resp_list = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
    target = next(u for u in resp_list.json() if u["email"] == "admin7b@example.com")

    resp = client.patch(
        f"/admin/users/{target['id']}/status",
        json={"is_admin": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True

    new_admin_token = register_and_login(client, "admin7b@example.com", "secret")
    resp_admin = client.get("/admin/users", headers={"Authorization": f"Bearer {new_admin_token}"})
    assert resp_admin.status_code == 200
