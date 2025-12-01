import pytest
from decimal import Decimal
from datetime import datetime, timezone, time
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.invoice_item import InvoiceItem
from backend.app.models.invoice_template import InvoiceTemplate
from backend.app.models.session import Session as TutoringSession
from backend.app.models.student import Student
from backend.app.models.user import User


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


def test_create_template():
    client = TestClient(app)
    token = register_and_login(client, "tmpl1@example.com", "secret")
    resp = client.post(
        "/invoice-templates",
        json={"name": "Standard", "default_rate": 80.0, "default_description": "Default tutoring"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Standard"
    assert data["default_rate"] == 80.0
    assert data["default_description"] == "Default tutoring"


def test_list_templates_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "tmpl2a@example.com", "secret")
    token_b = register_and_login(client, "tmpl2b@example.com", "secret")

    client.post(
        "/invoice-templates",
        json={"name": "A1"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    client.post(
        "/invoice-templates",
        json={"name": "A2"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    client.post(
        "/invoice-templates",
        json={"name": "B1"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    resp_a = client.get("/invoice-templates", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/invoice-templates", headers={"Authorization": f"Bearer {token_b}"})
    assert len(resp_a.json()) == 2
    assert len(resp_b.json()) == 1


def test_update_template():
    client = TestClient(app)
    token = register_and_login(client, "tmpl3@example.com", "secret")
    resp = client.post(
        "/invoice-templates",
        json={"name": "Old", "default_rate": 70.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    template_id = resp.json()["id"]

    update_resp = client.put(
        f"/invoice-templates/{template_id}",
        json={"name": "New", "default_rate": 90.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "New"
    assert data["default_rate"] == 90.0


def test_delete_template():
    client = TestClient(app)
    token = register_and_login(client, "tmpl4@example.com", "secret")
    resp = client.post(
        "/invoice-templates",
        json={"name": "ToDelete"},
        headers={"Authorization": f"Bearer {token}"},
    )
    template_id = resp.json()["id"]

    del_resp = client.delete(f"/invoice-templates/{template_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 200
    list_resp = client.get("/invoice-templates", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.json() == []


def test_invoice_item_can_reference_template():
    db = SessionLocal()
    try:
        user = User(email="owner@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        template = InvoiceTemplate(owner_id=user.id, name="Standard", default_rate=Decimal("80.00"))
        db.add(template)
        db.commit()
        db.refresh(template)

        student = Student(owner_id=user.id, parent_name="Parent", student_name="Student", status="new")
        db.add(student)
        db.commit()
        db.refresh(student)

        session = TutoringSession(
            owner_id=user.id,
            student_id=student.id,
            subject="Math",
            duration_minutes=60,
            session_date=datetime(2030, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            start_time=time(10, 0, 0),
            attendance_status="scheduled",
            billing_status="not_applicable",
            is_billable=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        item = InvoiceItem(
            session_id=session.id,
            student_id=student.id,
            owner_id=user.id,
            template_id=template.id,
            description="Math session",
            rate_per_hour=Decimal("80.00"),
            duration_minutes=60,
            cost_total=Decimal("80.00"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.template_id == template.id
    finally:
        db.close()
