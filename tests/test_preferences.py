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


def test_get_preferences_default_creates_record():
    client = TestClient(app)
    token = register_and_login(client, "prefs1@example.com", "secret")
    resp = client.get("/preferences/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "UTC"
    assert data["notifications_enabled"] is True
    assert data["locale"] == "en-US"


def test_update_timezone():
    client = TestClient(app)
    token = register_and_login(client, "prefs2@example.com", "secret")
    client.get("/preferences/me", headers={"Authorization": f"Bearer {token}"})

    resp = client.put(
        "/preferences/me",
        json={"timezone": "America/New_York"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "America/New_York"


def test_update_default_session_length():
    client = TestClient(app)
    token = register_and_login(client, "prefs3@example.com", "secret")
    client.get("/preferences/me", headers={"Authorization": f"Bearer {token}"})

    resp = client.put(
        "/preferences/me",
        json={"default_session_length": 90},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["default_session_length"] == 90


def test_partial_update():
    client = TestClient(app)
    token = register_and_login(client, "prefs4@example.com", "secret")
    client.get("/preferences/me", headers={"Authorization": f"Bearer {token}"})

    resp = client.put(
        "/preferences/me",
        json={"weekly_schedule_notes": "Evenings only"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["weekly_schedule_notes"] == "Evenings only"
    assert data["timezone"] == "UTC"


def test_boolean_toggle_notifications():
    client = TestClient(app)
    token = register_and_login(client, "prefs5@example.com", "secret")
    client.get("/preferences/me", headers={"Authorization": f"Bearer {token}"})

    resp = client.put(
        "/preferences/me",
        json={"notifications_enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["notifications_enabled"] is False


def test_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "prefs6a@example.com", "secret")
    token_b = register_and_login(client, "prefs6b@example.com", "secret")

    client.put(
        "/preferences/me",
        json={"timezone": "Asia/Tokyo"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp_b = client.get("/preferences/me", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert resp_b.json()["timezone"] == "UTC"
