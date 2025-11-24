import pytest
from decimal import Decimal
from datetime import datetime, timezone

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.models.invoice import Invoice
from backend.app.models.session import Session as TutoringSession
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.services.billing import (
    calculate_session_cost,
    create_invoice_for_student,
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_calculate_session_cost_basic():
    assert calculate_session_cost(60, Decimal("80.00")) == Decimal("80.00")
    assert calculate_session_cost(90, Decimal("80.00")) == Decimal("120.00")
    assert calculate_session_cost(None, Decimal("80.00")) is None
    assert calculate_session_cost(60, None) is None
    assert calculate_session_cost(0, Decimal("80.00")) is None


def _create_user_student(db):
    user = User(email="owner@example.com", hashed_password="x", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    student = Student(owner_id=user.id, parent_name="Parent", student_name="Student", status="active")
    db.add(student)
    db.commit()
    db.refresh(student)
    return user, student


def _create_session(db, owner_id, student_id, duration, rate, billing_status="not_applicable", is_billable=True):
    session = TutoringSession(
        owner_id=owner_id,
        student_id=student_id,
        subject="Math",
        duration_minutes=duration,
        session_date=datetime(2030, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        attendance_status="scheduled",
        billing_status=billing_status,
        is_billable=is_billable,
        rate_per_hour=rate,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_create_invoice_for_student_creates_invoice_and_items():
    db = SessionLocal()
    try:
        user, student = _create_user_student(db)
        s1 = _create_session(db, user.id, student.id, 60, Decimal("80.00"))
        s2 = _create_session(db, user.id, student.id, 30, Decimal("80.00"))

        invoice = create_invoice_for_student(db=db, owner_id=user.id, student_id=student.id)
        assert invoice is not None
        assert invoice.total_amount == Decimal("120.00")
        assert len(invoice.items) == 2
        assert all(item.cost_total in (Decimal("80.00"), Decimal("40.00")) for item in invoice.items)
        db.refresh(s1)
        db.refresh(s2)
        assert s1.billing_status == "invoiced"
        assert s2.billing_status == "invoiced"
    finally:
        db.close()


def test_create_invoice_for_student_skips_non_billable_sessions():
    db = SessionLocal()
    try:
        user, student = _create_user_student(db)
        billable = _create_session(db, user.id, student.id, 60, Decimal("100.00"))
        _create_session(db, user.id, student.id, 45, Decimal("100.00"), is_billable=False)
        _create_session(db, user.id, student.id, 30, Decimal("100.00"), billing_status="invoiced")

        invoice = create_invoice_for_student(db=db, owner_id=user.id, student_id=student.id)
        assert invoice is not None
        assert len(invoice.items) == 1
        assert invoice.total_amount == Decimal("100.00")
        db.refresh(billable)
        assert billable.billing_status == "invoiced"
    finally:
        db.close()


def test_create_invoice_for_student_returns_none_when_no_unbilled():
    db = SessionLocal()
    try:
        user, student = _create_user_student(db)
        _create_session(db, user.id, student.id, 60, Decimal("80.00"), billing_status="invoiced")

        invoice = create_invoice_for_student(db=db, owner_id=user.id, student_id=student.id)
        assert invoice is None
        assert db.query(Invoice).count() == 0
    finally:
        db.close()
