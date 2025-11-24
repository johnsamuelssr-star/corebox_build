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


def test_get_profile_requires_auth():
    client = TestClient(app)
    resp = client.get("/profile/me")
    assert resp.status_code == 401


def test_get_profile_defaults_for_new_user():
    client = TestClient(app)
    email = "profile@example.com"
    token = register_and_login(client, email, "secret")
    resp = client.get("/profile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert data["first_name"] is None
    assert data["last_name"] is None
    assert data["phone"] is None
    assert data["organization_name"] is None
    assert data["avatar_url"] is None
    assert data["bio"] is None


def test_update_profile_fields():
    client = TestClient(app)
    token = register_and_login(client, "profile2@example.com", "secret")
    payload = {
        "first_name": "Annie",
        "last_name": "Tutor",
        "phone": "904-555-1212",
        "organization_name": "Mindfull Learning",
        "avatar_url": "https://example.com/avatar.png",
        "bio": "Math and science tutor.",
    }
    resp = client.put("/profile/me", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    for key, value in payload.items():
        assert data[key] == value

    resp_get = client.get("/profile/me", headers={"Authorization": f"Bearer {token}"})
    data_get = resp_get.json()
    for key, value in payload.items():
        assert data_get[key] == value


def test_partial_update_profile():
    client = TestClient(app)
    token = register_and_login(client, "profile3@example.com", "secret")
    payload = {
        "first_name": "Full",
        "last_name": "Profile",
        "phone": "000-000-0000",
        "organization_name": "Org",
        "avatar_url": "https://example.com/full.png",
        "bio": "Full bio",
    }
    client.put("/profile/me", json=payload, headers={"Authorization": f"Bearer {token}"})

    resp = client.put(
        "/profile/me",
        json={"phone": "111-222-3333"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "111-222-3333"
    assert data["first_name"] == payload["first_name"]
    assert data["last_name"] == payload["last_name"]
    assert data["organization_name"] == payload["organization_name"]
    assert data["avatar_url"] == payload["avatar_url"]
    assert data["bio"] == payload["bio"]


def test_profile_does_not_allow_email_change():
    client = TestClient(app)
    email = "profile4@example.com"
    token = register_and_login(client, email, "secret")
    resp = client.put(
        "/profile/me",
        json={"email": "newemail@example.com", "first_name": "New"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert data["first_name"] == "New"
