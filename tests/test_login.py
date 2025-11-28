import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_user(client: TestClient, email: str, password: str):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_successful_login_returns_token():
    client = TestClient(app)
    register_user(client, "login@example.com", "secret")
    response = client.post("/auth/login", json={"email": "login@example.com", "password": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("token_type") == "bearer"
    assert isinstance(data.get("access_token"), str) and data["access_token"]


def test_wrong_password_returns_400():
    client = TestClient(app)
    register_user(client, "wrongpw@example.com", "secret")
    response = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "bad"})
    assert response.status_code == 400


def test_missing_hash_returns_400_not_500():
    client = TestClient(app)
    # Create user with empty hash to simulate bad data
    register_user(client, "badhash@example.com", "secret")
    # Manually clear hash
    db = SessionLocal()
    user = db.query(User).filter(User.email == "badhash@example.com").first()
    user.hashed_password = None
    db.add(user)
    db.commit()
    db.close()
    response = client.post("/auth/login", json={"email": "badhash@example.com", "password": "secret"})
    assert response.status_code == 400


def test_user_query_no_ambiguous_fk():
    db = SessionLocal()
    user = User(email="query@example.com", hashed_password="dummy")
    db.add(user)
    db.commit()
    users = db.query(User).all()
    assert len(users) == 1
    db.close()


def test_nonexistent_user_returns_400():
    client = TestClient(app)
    response = client.post("/auth/login", json={"email": "nosuch@example.com", "password": "secret"})
    assert response.status_code == 400


def test_token_type_is_bearer():
    client = TestClient(app)
    register_user(client, "typecheck@example.com", "secret")
    response = client.post("/auth/login", json={"email": "typecheck@example.com", "password": "secret"})
    assert response.status_code == 200
    assert response.json().get("token_type") == "bearer"
