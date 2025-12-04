import pytest
from decimal import Decimal
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


def test_get_rate_settings_creates_defaults():
    client = TestClient(app)
    token = register_and_login(client, "rates1@example.com", "secret")
    resp = client.get("/settings/rates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["hourly_rate"]) == Decimal("60.00")
    assert Decimal(data["half_hour_rate"]) == Decimal("40.00")
    assert Decimal(data["regular_rate_60"]) == Decimal("60.00")
    assert Decimal(data["regular_rate_45"]) == Decimal("45.00")
    assert Decimal(data["regular_rate_30"]) == Decimal("30.00")
    assert Decimal(data["discount_rate_60"]) == Decimal("60.00")
    assert Decimal(data["discount_rate_45"]) == Decimal("45.00")
    assert Decimal(data["discount_rate_30"]) == Decimal("30.00")


def test_update_rate_settings():
    client = TestClient(app)
    token = register_and_login(client, "rates2@example.com", "secret")
    resp = client.put(
        "/settings/rates",
        json={
            "hourly_rate": "90.00",
            "half_hour_rate": "50.00",
            "regular_rate_60": "100.00",
            "regular_rate_45": "80.00",
            "regular_rate_30": "60.00",
            "discount_rate_60": "90.00",
            "discount_rate_45": "70.00",
            "discount_rate_30": "50.00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["hourly_rate"]) == Decimal("90.00")
    assert Decimal(data["half_hour_rate"]) == Decimal("50.00")
    assert Decimal(data["regular_rate_60"]) == Decimal("100.00")
    assert Decimal(data["regular_rate_45"]) == Decimal("80.00")
    assert Decimal(data["regular_rate_30"]) == Decimal("60.00")
    assert Decimal(data["discount_rate_60"]) == Decimal("90.00")
    assert Decimal(data["discount_rate_45"]) == Decimal("70.00")
    assert Decimal(data["discount_rate_30"]) == Decimal("50.00")
