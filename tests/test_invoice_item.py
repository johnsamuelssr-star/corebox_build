import pytest
from decimal import Decimal
from datetime import datetime, timezone, time

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.models.invoice_item import InvoiceItem
from backend.app.models.session import Session as TutoringSession
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.models.invoice_template import InvoiceTemplate


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_invoice_item_persists_and_relations_work():
    db = SessionLocal()
    try:
        user = User(email="owner@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

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
            description="Algebra session",
            rate_per_hour=Decimal("80.00"),
            duration_minutes=60,
            cost_total=Decimal("80.00"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.id is not None
        assert item.session.id == session.id
        assert item.owner.id == user.id
        assert item.student.id == student.id
        assert item.cost_total == Decimal("80.00")
    finally:
        db.close()
