"""Billing service utilities."""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.invoice_item import InvoiceItem
from backend.app.models.payment import Payment
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.models.user import User


def calculate_session_cost(duration_minutes: int | None, rate_per_hour: Decimal | float | None) -> Decimal | None:
    """Compute session cost using Decimal math; return None for invalid inputs."""
    if duration_minutes is None or rate_per_hour is None:
        return None
    if duration_minutes <= 0:
        return None
    rate = Decimal(str(rate_per_hour))
    if rate <= 0:
        return None
    hours = Decimal(duration_minutes) / Decimal("60")
    cost = hours * rate
    return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_unbilled_sessions_for_student(db: Session, owner_id: int, student_id: int) -> List[SessionModel]:
    """Return billable sessions not yet invoiced for the given owner/student."""
    query = (
        db.query(SessionModel)
        .filter(
            SessionModel.owner_id == owner_id,
            SessionModel.student_id == student_id,
            SessionModel.is_billable.is_(True),
            SessionModel.billing_status.notin_(["invoiced", "paid"]),
        )
    )
    return query.all()


def recalculate_invoice_totals(invoice: Invoice) -> None:
    paid = sum((p.amount for p in invoice.payments if p.amount is not None), Decimal("0.00"))
    total = invoice.total_amount or Decimal("0.00")
    invoice.amount_paid = paid
    balance = total - paid
    if balance < Decimal("0.00"):
        balance = Decimal("0.00")
    invoice.balance_due = balance


def determine_invoice_status(invoice: Invoice, now: datetime | None = None) -> str:
    if invoice.status in ("void", "written_off"):
        return invoice.status
    if invoice.total_amount is None:
        return invoice.status
    if invoice.balance_due <= 0:
        return "paid"
    if invoice.amount_paid > 0 and invoice.balance_due > 0:
        return "partial"
    check_date = now or datetime.now(timezone.utc)
    if invoice.due_date and check_date > invoice.due_date:
        return "overdue"
    if invoice.amount_paid == 0:
        return "unpaid"
    return "open"


def apply_payment_to_invoice(invoice: Invoice, amount: Decimal | float) -> Payment:
    payment_amount = Decimal(str(amount))
    payment = Payment(owner_id=invoice.owner_id, invoice_id=invoice.id, amount=payment_amount)
    invoice.payments.append(payment)
    recalculate_invoice_totals(invoice)
    invoice.status = determine_invoice_status(invoice)
    return payment


def create_invoice_for_student(
    db: Session,
    owner_id: int,
    student_id: int,
    status: str = "draft",
    due_date: datetime | None = None,
) -> Invoice | None:
    sessions = get_unbilled_sessions_for_student(db, owner_id=owner_id, student_id=student_id)
    invoice_items: list[InvoiceItem] = []

    for session in sessions:
        cost = session.cost_total
        if cost is None:
            cost = calculate_session_cost(session.duration_minutes, session.rate_per_hour)
            session.cost_total = cost
        if cost is None:
            continue
        item = InvoiceItem(
            session_id=session.id,
            student_id=session.student_id,
            owner_id=owner_id,
            description=f"Session on {session.session_date} - {session.subject}",
            rate_per_hour=session.rate_per_hour,
            duration_minutes=session.duration_minutes,
            cost_total=cost,
        )
        invoice_items.append(item)
        session.billing_status = "invoiced"

    if not invoice_items:
        return None

    total_amount = sum((item.cost_total for item in invoice_items if item.cost_total is not None), Decimal("0.00"))

    invoice = Invoice(
        owner_id=owner_id,
        student_id=student_id,
        status=status,
        total_amount=total_amount,
        amount_paid=Decimal("0.00"),
        balance_due=total_amount,
        due_date=due_date,
    )
    db.add(invoice)
    db.flush()  # obtain invoice id for invoice_items
    for item in invoice_items:
        item.invoice_id = invoice.id
        db.add(item)
    db.commit()
    db.refresh(invoice)
    for item in invoice_items:
        db.refresh(item)
    return invoice
