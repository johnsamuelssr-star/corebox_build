import pytest
from decimal import Decimal
from datetime import datetime, timezone, time

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.models.invoice import Invoice
from backend.app.models.invoice_item import InvoiceItem
from backend.app.models.payment import Payment
from backend.app.models.session import Session as TutoringSession
from backend.app.models.student import Student
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user_student_invoice(db):
    user = User(email="owner@example.com", hashed_password="x", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    student = Student(owner_id=user.id, parent_name="Parent", student_name="Student", status="active")
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
        rate_per_hour=Decimal("80.00"),
        cost_total=Decimal("80.00"),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    invoice = Invoice(owner_id=user.id, student_id=student.id, total_amount=Decimal("80.00"), status="draft")
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    item = InvoiceItem(
        session_id=session.id,
        student_id=student.id,
        owner_id=user.id,
        invoice_id=invoice.id,
        description="Math session",
        rate_per_hour=Decimal("80.00"),
        duration_minutes=60,
        cost_total=Decimal("80.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return user, invoice


def test_payment_persists_and_relations_work():
    db = SessionLocal()
    try:
        user, invoice = _create_user_student_invoice(db)
        payment = Payment(
            owner_id=user.id,
            invoice_id=invoice.id,
            amount=Decimal("80.00"),
            method="cash",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        assert payment.id is not None
        assert payment.invoice_id == invoice.id
        assert payment.owner_id == user.id
        assert payment.invoice.id == invoice.id
        assert payment.invoice.payments[0].id == payment.id
    finally:
        db.close()


def test_payment_timestamps_set():
    db = SessionLocal()
    try:
        user, invoice = _create_user_student_invoice(db)
        payment = Payment(owner_id=user.id, invoice_id=invoice.id, amount=Decimal("50.00"))
        db.add(payment)
        db.commit()
        db.refresh(payment)

        assert payment.created_at is not None
        assert payment.updated_at is not None
        assert payment.received_at is not None
    finally:
        db.close()


def test_payment_amount_precision():
    db = SessionLocal()
    try:
        user, invoice = _create_user_student_invoice(db)
        payment = Payment(owner_id=user.id, invoice_id=invoice.id, amount=Decimal("123.45"))
        db.add(payment)
        db.commit()
        db.refresh(payment)

        assert payment.amount == Decimal("123.45")
    finally:
        db.close()
