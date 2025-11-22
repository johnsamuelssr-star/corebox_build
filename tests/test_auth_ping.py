from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_auth_ping():
    response = client.get("/auth/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
