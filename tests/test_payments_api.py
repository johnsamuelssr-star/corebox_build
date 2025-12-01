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


def create_student(client: TestClient, token: str):
    resp = client.post(
        "/students",
        json={"parent_name": "Parent", "student_name": "Student"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def create_session(client: TestClient, token: str, student_id: int, rate: float, duration: int):
    resp = client.post(
        "/sessions",
        json={
            "student_id": student_id,
            "subject": "Math",
            "duration_minutes": duration,
            "session_date": "2030-01-01T10:00:00Z",
            "start_time": "10:00:00",
            "rate_per_hour": rate,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def generate_invoice(client: TestClient, token: str, student_id: int):
    resp = client.post(f"/invoices/{student_id}/generate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    return resp.json()


def test_apply_payment_marks_invoice_paid_when_fully_covered():
    client = TestClient(app)
    token = register_and_login(client, "pay1@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)

    pay_resp = client.post(
        f"/invoices/{invoice['id']}/payments",
        json={"invoice_id": invoice["id"], "amount": "100.00", "method": "cash"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pay_resp.status_code == 201
    inv_resp = client.get(f"/invoices/{invoice['id']}", headers={"Authorization": f"Bearer {token}"})
    data = inv_resp.json()
    assert str(data["amount_paid"]).startswith("100")
    assert str(data["balance_due"]).startswith("0")
    assert data["status"] == "paid"


def test_apply_partial_payment_sets_status_partial():
    client = TestClient(app)
    token = register_and_login(client, "pay2@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)

    pay_resp = client.post(
        f"/invoices/{invoice['id']}/payments",
        json={"invoice_id": invoice["id"], "amount": "40.00", "method": "cash"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pay_resp.status_code == 201
    inv_resp = client.get(f"/invoices/{invoice['id']}", headers={"Authorization": f"Bearer {token}"})
    data = inv_resp.json()
    assert str(data["amount_paid"]).startswith("40")
    assert str(data["balance_due"]).startswith("60")
    assert data["status"] == "partial"


def test_overpayment_sets_paid_and_zero_balance():
    client = TestClient(app)
    token = register_and_login(client, "pay3@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 100.0, 60)
    invoice = generate_invoice(client, token, student_id)

    pay_resp = client.post(
        f"/invoices/{invoice['id']}/payments",
        json={"invoice_id": invoice["id"], "amount": "150.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pay_resp.status_code == 201
    inv_resp = client.get(f"/invoices/{invoice['id']}", headers={"Authorization": f"Bearer {token}"})
    data = inv_resp.json()
    assert str(data["balance_due"]).startswith("0")
    assert data["status"] == "paid"


def test_cannot_apply_payment_to_other_users_invoice():
    client = TestClient(app)
    token_a = register_and_login(client, "pay4a@example.com", "secret")
    token_b = register_and_login(client, "pay4b@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 80.0, 60)
    invoice = generate_invoice(client, token_a, student_a)

    resp = client.post(
        f"/invoices/{invoice['id']}/payments",
        json={"invoice_id": invoice["id"], "amount": "80.00"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


def test_cannot_apply_payment_to_void_invoice():
    client = TestClient(app)
    token = register_and_login(client, "pay5@example.com", "secret")
    student_id = create_student(client, token)
    create_session(client, token, student_id, 80.0, 60)
    invoice = generate_invoice(client, token, student_id)

    client.patch(
        f"/invoices/{invoice['id']}",
        json={"status": "void"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        f"/invoices/{invoice['id']}/payments",
        json={"invoice_id": invoice["id"], "amount": "80.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_list_payments_returns_only_current_user_payments():
    client = TestClient(app)
    token_a = register_and_login(client, "paylist1@example.com", "secret")
    token_b = register_and_login(client, "paylist2@example.com", "secret")

    student_a = create_student(client, token_a)
    create_session(client, token_a, student_a, 50.0, 60)
    invoice_a = generate_invoice(client, token_a, student_a)
    client.post(
        f"/invoices/{invoice_a['id']}/payments",
        json={"invoice_id": invoice_a["id"], "amount": "50.00"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    student_b = create_student(client, token_b)
    create_session(client, token_b, student_b, 60.0, 60)
    invoice_b = generate_invoice(client, token_b, student_b)
    client.post(
        f"/invoices/{invoice_b['id']}/payments",
        json={"invoice_id": invoice_b["id"], "amount": "60.00"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    resp = client.get("/payments", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["invoice_id"] == invoice_a["id"] for p in data)


def test_list_payments_can_filter_by_invoice_id():
    client = TestClient(app)
    token = register_and_login(client, "paylist3@example.com", "secret")
    student = create_student(client, token)
    create_session(client, token, student, 50.0, 60)
    invoice1 = generate_invoice(client, token, student)
    client.post(
        f"/invoices/{invoice1['id']}/payments",
        json={"invoice_id": invoice1["id"], "amount": "50.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    create_session(client, token, student, 75.0, 60)
    invoice2 = generate_invoice(client, token, student)
    client.post(
        f"/invoices/{invoice2['id']}/payments",
        json={"invoice_id": invoice2["id"], "amount": "75.00"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get("/payments", params={"invoice_id": invoice1["id"]}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["invoice_id"] == invoice1["id"] for p in data)


def test_list_payments_filters_by_amount_range():
    client = TestClient(app)
    token = register_and_login(client, "paylist4@example.com", "secret")
    student = create_student(client, token)
    create_session(client, token, student, 50.0, 60)
    invoice = generate_invoice(client, token, student)
    for amt in ["50.00", "100.00", "200.00"]:
        client.post(
            f"/invoices/{invoice['id']}/payments",
            json={"invoice_id": invoice["id"], "amount": amt},
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = client.get(
        "/payments",
        params={"min_amount": "75", "max_amount": "150"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    amounts = {str(p["amount"]) for p in data}
    assert amounts == {"100.00"}


def test_list_payments_invalid_sort_by_400():
    client = TestClient(app)
    token = register_and_login(client, "paylist5@example.com", "secret")
    resp = client.get("/payments", params={"sort_by": "not_a_field"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_list_payments_invalid_sort_order_400():
    client = TestClient(app)
    token = register_and_login(client, "paylist6@example.com", "secret")
    resp = client.get("/payments", params={"sort_order": "sideways"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
