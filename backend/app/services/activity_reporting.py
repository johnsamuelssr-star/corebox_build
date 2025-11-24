"""Activity reporting helpers for sessions and students."""

from datetime import date
from decimal import Decimal
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student


def get_activity_summary(db: Session, *, owner_id: int, start_date: date | None = None) -> Dict:
    """Return aggregated activity summary for an owner."""
    session_query = db.query(SessionModel).filter(SessionModel.owner_id == owner_id)
    if start_date:
        session_query = session_query.filter(func.date(SessionModel.session_date) >= start_date)
    sessions = session_query.all()

    session_count = len(sessions)
    total_minutes = sum((s.duration_minutes or 0) for s in sessions)
    total_hours = Decimal(total_minutes) / Decimal("60")

    invoice_query = db.query(Invoice).filter(Invoice.owner_id == owner_id)
    if start_date:
        invoice_query = invoice_query.filter(func.date(Invoice.created_at) >= start_date)
    invoices = invoice_query.all()
    invoice_ids = [inv.id for inv in invoices]

    total_invoiced = sum((inv.total_amount or Decimal("0.00") for inv in invoices), Decimal("0.00"))
    total_outstanding = sum(
        (Decimal(str(inv.balance_due or 0)) for inv in invoices),
        Decimal("0.00"),
    )

    total_paid = Decimal("0.00")
    if invoice_ids:
        pay_sum = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.invoice_id.in_(invoice_ids))
            .scalar()
        )
        total_paid = Decimal(str(pay_sum or 0))

    # Per-student aggregation
    students = db.query(Student).filter(Student.owner_id == owner_id).all()
    student_summaries = []
    for student in students:
        stu_sessions = [s for s in sessions if s.student_id == student.id]
        stu_minutes = sum((s.duration_minutes or 0) for s in stu_sessions)
        stu_hours = Decimal(stu_minutes) / Decimal("60")

        stu_invoices = [inv for inv in invoices if inv.student_id == student.id]
        stu_invoice_ids = [inv.id for inv in stu_invoices]
        stu_total_invoiced = sum((inv.total_amount or Decimal("0.00") for inv in stu_invoices), Decimal("0.00"))
        stu_outstanding = sum(
            (Decimal(str(inv.balance_due or 0)) for inv in stu_invoices),
            Decimal("0.00"),
        )
        stu_paid = Decimal("0.00")
        if stu_invoice_ids:
            stu_pay_sum = (
                db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(Payment.invoice_id.in_(stu_invoice_ids))
                .scalar()
            )
            stu_paid = Decimal(str(stu_pay_sum or 0))

        student_summaries.append(
            {
                "student_id": student.id,
                "student_display_name": student.student_name,
                "session_count": len(stu_sessions),
                "hours": str(stu_hours.quantize(Decimal("0.01"))),
                "total_invoiced": str(stu_total_invoiced.quantize(Decimal("0.01"))),
                "total_paid": str(stu_paid.quantize(Decimal("0.01"))),
                "total_outstanding": str(stu_outstanding.quantize(Decimal("0.01"))),
            }
        )

    summary = {
        "session_count": session_count,
        "total_hours": str(total_hours.quantize(Decimal("0.01"))),
        "total_invoiced": str(total_invoiced.quantize(Decimal("0.01"))),
        "total_paid": str(total_paid.quantize(Decimal("0.01"))),
        "total_outstanding": str(total_outstanding.quantize(Decimal("0.01"))),
        "students": student_summaries,
    }
    return summary
