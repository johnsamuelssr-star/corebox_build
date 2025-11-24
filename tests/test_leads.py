import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.models.lead import Lead


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_lead(client: TestClient, token: str, payload: dict):
    return client.post("/leads", json=payload, headers={"Authorization": f"Bearer {token}"})


def test_create_lead_success():
    client = TestClient(app)
    token = register_and_login(client, "lead@example.com", "secret")
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 5,
        "status": "new",
        "notes": "Interested",
    }
    response = create_lead(client, token, payload)
    assert response.status_code == 200
    data = response.json()
    for key in ["parent_name", "student_name", "grade_level", "status", "notes"]:
        assert data[key] == payload[key]
    assert isinstance(data.get("id"), int)


def test_list_leads_returns_user_leads():
    client = TestClient(app)
    token = register_and_login(client, "list@example.com", "secret")
    payload = {
        "parent_name": "Parent2",
        "student_name": "Student2",
        "grade_level": 6,
        "status": "contacted",
        "notes": None,
    }
    create_lead(client, token, payload)
    response = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["parent_name"] == payload["parent_name"]


def test_create_lead_requires_auth():
    client = TestClient(app)
    payload = {
        "parent_name": "NoAuth",
        "student_name": "Student",
        "grade_level": 4,
        "status": "new",
        "notes": None,
    }
    response = client.post("/leads", json=payload)
    assert response.status_code == 401


def test_invalid_status_rejected():
    client = TestClient(app)
    token = register_and_login(client, "badstatus@example.com", "secret")
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 3,
        "status": "invalid",
        "notes": None,
    }
    response = create_lead(client, token, payload)
    assert response.status_code == 422


def test_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "a@example.com", "secret")
    token_b = register_and_login(client, "b@example.com", "secret")

    payload = {
        "parent_name": "ParentA",
        "student_name": "StudentA",
        "grade_level": 2,
        "status": "new",
        "notes": None,
    }
    create_response = create_lead(client, token_a, payload)
    assert create_response.status_code == 200

    response_b = client.get("/leads", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert data_b == []


def test_get_single_lead_for_owner():
    client = TestClient(app)
    token = register_and_login(client, "single@example.com", "secret")
    payload = {
        "parent_name": "Parent",
        "student_name": "Student",
        "grade_level": 1,
        "status": "new",
        "notes": None,
    }
    create_response = create_lead(client, token, payload)
    lead_id = create_response.json()["id"]

    response = client.get(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == lead_id


def test_get_lead_not_owned_returns_404():
    client = TestClient(app)
    token_a = register_and_login(client, "owner@example.com", "secret")
    token_b = register_and_login(client, "other@example.com", "secret")
    create_response = create_lead(
        client,
        token_a,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = create_response.json()["id"]

    response = client.get(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_update_lead_for_owner():
    client = TestClient(app)
    token = register_and_login(client, "update@example.com", "secret")
    create_response = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = create_response.json()["id"]

    response = client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted", "notes": "Called once"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "contacted"
    assert data["notes"] == "Called once"

    follow_up = client.get(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token}"})
    assert follow_up.status_code == 200
    assert follow_up.json()["status"] == "contacted"


def test_delete_lead_for_owner():
    client = TestClient(app)
    token = register_and_login(client, "delete@example.com", "secret")
    create_response = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = create_response.json()["id"]

    response = client.delete(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    follow_up = client.get(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token}"})
    assert follow_up.status_code == 404


def test_update_or_delete_lead_not_owned_returns_404():
    client = TestClient(app)
    token_a = register_and_login(client, "owner2@example.com", "secret")
    token_b = register_and_login(client, "other2@example.com", "secret")
    create_response = create_lead(
        client,
        token_a,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = create_response.json()["id"]

    update_resp = client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert update_resp.status_code == 404

    delete_resp = client.delete(f"/leads/{lead_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert delete_resp.status_code == 404


def test_filter_leads_by_status():
    client = TestClient(app)
    token = register_and_login(client, "filter@example.com", "secret")
    leads = [
        {"parent_name": "P1", "student_name": "S1", "grade_level": 1, "status": "new", "notes": None},
        {"parent_name": "P2", "student_name": "S2", "grade_level": 2, "status": "contacted", "notes": None},
        {"parent_name": "P3", "student_name": "S3", "grade_level": 3, "status": "trial_scheduled", "notes": None},
    ]
    for payload in leads:
        create_lead(client, token, payload)

    response = client.get("/leads", params={"status": "contacted"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "contacted"


def test_search_leads_by_name():
    client = TestClient(app)
    token = register_and_login(client, "search@example.com", "secret")
    leads = [
        {"parent_name": "Alice Johnson", "student_name": "Student1", "grade_level": 1, "status": "new", "notes": None},
        {"parent_name": "Bob Smith", "student_name": "Student2", "grade_level": 2, "status": "new", "notes": None},
        {"parent_name": "Alicia Stone", "student_name": "Student3", "grade_level": 3, "status": "new", "notes": None},
    ]
    for payload in leads:
        create_lead(client, token, payload)

    response = client.get("/leads", params={"search": "ali"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    names = [lead["parent_name"].lower() for lead in response.json()]
    assert "alice johnson" in names
    assert "alicia stone" in names
    assert "bob smith" not in names


def test_leads_pagination():
    client = TestClient(app)
    token = register_and_login(client, "paginate@example.com", "secret")
    for i in range(5):
        create_lead(
            client,
            token,
            {
                "parent_name": f"Parent{i}",
                "student_name": f"Student{i}",
                "grade_level": i,
                "status": "new",
                "notes": None,
            },
        )

    page1 = client.get("/leads", params={"skip": 0, "limit": 2}, headers={"Authorization": f"Bearer {token}"})
    page2 = client.get("/leads", params={"skip": 2, "limit": 2}, headers={"Authorization": f"Bearer {token}"})

    assert page1.status_code == 200
    assert page2.status_code == 200

    leads_page1 = page1.json()
    leads_page2 = page2.json()
    assert len(leads_page1) == 2
    assert len(leads_page2) == 2

    ids_page1 = {lead["id"] for lead in leads_page1}
    ids_page2 = {lead["id"] for lead in leads_page2}
    assert ids_page1.isdisjoint(ids_page2)


def test_filters_do_not_cross_owners():
    client = TestClient(app)
    token_a = register_and_login(client, "filtera@example.com", "secret")
    token_b = register_and_login(client, "filterb@example.com", "secret")

    create_lead(
        client,
        token_a,
        {
            "parent_name": "Alice A",
            "student_name": "StudentA",
            "grade_level": 1,
            "status": "contacted",
            "notes": None,
        },
    )
    create_lead(
        client,
        token_b,
        {
            "parent_name": "Alice B",
            "student_name": "StudentB",
            "grade_level": 2,
            "status": "contacted",
            "notes": None,
        },
    )

    response_a = client.get(
        "/leads",
        params={"status": "contacted", "search": "alice"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert len(data_a) == 1
    assert data_a[0]["parent_name"] == "Alice A"


def test_default_sort_by_created_at_desc():
    client = TestClient(app)
    token = register_and_login(client, "sortdefault@example.com", "secret")
    payloads = [
        {"parent_name": "First", "student_name": "S1", "grade_level": 1, "status": "new", "notes": None},
        {"parent_name": "Second", "student_name": "S2", "grade_level": 2, "status": "new", "notes": None},
        {"parent_name": "Third", "student_name": "S3", "grade_level": 3, "status": "new", "notes": None},
    ]
    for payload in payloads:
        create_lead(client, token, payload)

    response = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    names = [lead["parent_name"] for lead in response.json()]
    assert names[0] == "Third"
    assert names[-1] == "First"


def test_sort_by_status_asc():
    client = TestClient(app)
    token = register_and_login(client, "sortstatus@example.com", "secret")
    statuses = ["new", "contacted", "trial_scheduled", "enrolled"]
    for idx, status in enumerate(statuses):
        create_lead(
            client,
            token,
            {"parent_name": f"P{idx}", "student_name": f"S{idx}", "grade_level": idx, "status": status, "notes": None},
        )

    response = client.get("/leads", params={"sort_by": "status", "sort_order": "asc"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    returned_statuses = [lead["status"] for lead in response.json()]
    assert returned_statuses == sorted(statuses)


def test_sort_by_grade_level_desc():
    client = TestClient(app)
    token = register_and_login(client, "sortgrade@example.com", "secret")
    grades = [3, 8, 5]
    for grade in grades:
        create_lead(
            client,
            token,
            {"parent_name": f"P{grade}", "student_name": f"S{grade}", "grade_level": grade, "status": "new", "notes": None},
        )

    response = client.get("/leads", params={"sort_by": "grade_level", "sort_order": "desc"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    returned_grades = [lead["grade_level"] for lead in response.json()]
    assert returned_grades == sorted(grades, reverse=True)


def test_invalid_sort_by_400():
    client = TestClient(app)
    token = register_and_login(client, "sortinvalid@example.com", "secret")
    response = client.get("/leads", params={"sort_by": "unknown_field"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "Invalid sort_by value" in response.json()["detail"]


def test_invalid_sort_order_400():
    client = TestClient(app)
    token = register_and_login(client, "sortorderinvalid@example.com", "secret")
    response = client.get("/leads", params={"sort_by": "created_at", "sort_order": "sideways"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "Invalid sort_order value" in response.json()["detail"]


def test_sort_respects_owner_isolation():
    client = TestClient(app)
    token_a = register_and_login(client, "sortiso_a@example.com", "secret")
    token_b = register_and_login(client, "sortiso_b@example.com", "secret")

    create_lead(client, token_a, {"parent_name": "A1", "student_name": "SA1", "grade_level": 1, "status": "new", "notes": None})
    create_lead(client, token_b, {"parent_name": "B1", "student_name": "SB1", "grade_level": 2, "status": "contacted", "notes": None})

    response = client.get("/leads", params={"sort_by": "created_at", "sort_order": "asc"}, headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 200
    data = response.json()
    assert all("A" in lead["parent_name"] for lead in data)


def test_search_leads_by_multiple_tokens():
    client = TestClient(app)
    token = register_and_login(client, "multisearch@example.com", "secret")
    leads = [
        {"parent_name": "Alice Johnson", "student_name": "Mark", "grade_level": 7, "status": "new", "notes": "7th grade math"},
        {"parent_name": "Bob Smith", "student_name": "Alicia Stone", "grade_level": 8, "status": "new", "notes": "algebra"},
        {"parent_name": "John Doe", "student_name": "Chris", "grade_level": 9, "status": "new", "notes": "history only"},
    ]
    for payload in leads:
        create_lead(client, token, payload)

    response = client.get("/leads", params={"search": "ali math"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    results = response.json()
    assert all("john doe" not in lead["parent_name"].lower() for lead in results)
    for lead in results:
        combined = " ".join(
            [
                lead.get("parent_name", "") or "",
                lead.get("student_name", "") or "",
                lead.get("notes", "") or "",
            ]
        ).lower()
        assert "ali" in combined
        assert "math" in combined


def test_search_leads_matches_notes_field():
    client = TestClient(app)
    token = register_and_login(client, "notesearch@example.com", "secret")
    payload = {
        "parent_name": "Parent X",
        "student_name": "Student X",
        "grade_level": 5,
        "status": "new",
        "notes": "Highly motivated, loves robotics",
    }
    create_lead(client, token, payload)

    response = client.get("/leads", params={"search": "robotics"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "robotics" in data[0]["notes"].lower()


def test_search_is_owner_isolated():
    client = TestClient(app)
    token_a = register_and_login(client, "searchiso_a@example.com", "secret")
    token_b = register_and_login(client, "searchiso_b@example.com", "secret")

    create_lead(
        client,
        token_a,
        {"parent_name": "Parent A", "student_name": "Student A", "grade_level": 1, "status": "new", "notes": "PRIVATEKEYWORD note"},
    )
    response = client.get("/leads", params={"search": "PRIVATEKEYWORD"}, headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 200
    assert response.json() == []


def test_valid_status_transitions():
    client = TestClient(app)
    token = register_and_login(client, "statusflow@example.com", "secret")
    create_response = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    )
    lead_id = create_response.json()["id"]
    with SessionLocal() as db:
        record = db.query(Lead).filter(Lead.id == lead_id).first()
    status_chain = ["contacted", "trial_scheduled", "enrolled"]
    previous_timestamp = record.status_changed_at

    for new_status in status_chain:
        resp = client.put(
            f"/leads/{lead_id}",
            json={"status": new_status},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        with SessionLocal() as db:
            record = db.query(Lead).filter(Lead.id == lead_id).first()
        assert record.status == new_status
        assert record.status_changed_at != previous_timestamp
        previous_timestamp = record.status_changed_at


def test_invalid_status_skip_enforced():
    client = TestClient(app)
    token = register_and_login(client, "invalidflow@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    resp = client.put(
        f"/leads/{lead_id}",
        json={"status": "enrolled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["detail"]


def test_cannot_change_status_from_closed_lost():
    client = TestClient(app)
    token = register_and_login(client, "closedlost@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    close_resp = client.put(
        f"/leads/{lead_id}",
        json={"status": "closed_lost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert close_resp.status_code == 200

    resp = client.put(
        f"/leads/{lead_id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_non_status_update_does_not_change_status_changed_at():
    client = TestClient(app)
    token = register_and_login(client, "nostatuschange@example.com", "secret")
    lead_id = create_lead(
        client,
        token,
        {
            "parent_name": "Parent",
            "student_name": "Student",
            "grade_level": 1,
            "status": "new",
            "notes": None,
        },
    ).json()["id"]

    with SessionLocal() as db:
        record_before = db.query(Lead).filter(Lead.id == lead_id).first()

    resp = client.put(
        f"/leads/{lead_id}",
        json={"notes": "Updated note"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        record_after = db.query(Lead).filter(Lead.id == lead_id).first()

    assert record_after.status == "new"
    assert record_after.status_changed_at == record_before.status_changed_at
