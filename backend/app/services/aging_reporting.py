"""Owner-level aging summary reporting."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.student import Student


def _init_buckets() -> Dict[str, Decimal]:
    return {
        "current": Decimal("0.00"),
        "days_1_30": Decimal("0.00"),
        "days_31_60": Decimal("0.00"),
        "days_61_90": Decimal("0.00"),
        "days_90_plus": Decimal("0.00"),
    }


def _bucket_for_days(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "days_1_30"
    if days_past_due <= 60:
        return "days_31_60"
    if days_past_due <= 90:
        return "days_61_90"
    return "days_90_plus"


def get_aging_summary(db: Session, *, owner_id: int, as_of: date | None = None) -> dict:
    """Compute aging summary for an owner scoped by outstanding invoices."""
    as_of_date = as_of or datetime.now(timezone.utc).date()

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.owner_id == owner_id,
            Invoice.balance_due > Decimal("0.00"),
            Invoice.status.notin_(["paid", "void", "written_off"]),
        )
        .all()
    )

    totals = _init_buckets()
    per_student: Dict[int, Dict[str, Decimal]] = {}

    for inv in invoices:
        balance = Decimal(str(inv.balance_due or 0)).quantize(Decimal("0.01"))
        due_date = inv.due_date.date() if inv.due_date else None
        if due_date is None:
            bucket = "current"
        else:
            days_past_due = (as_of_date - due_date).days
            bucket = _bucket_for_days(days_past_due)

        totals[bucket] += balance
        per_student.setdefault(inv.student_id, _init_buckets())[bucket] += balance

    students_rows = []
    if per_student:
        student_map = {
            stu.id: stu
            for stu in db.query(Student).filter(Student.owner_id == owner_id, Student.id.in_(per_student.keys())).all()
        }
        for student_id, buckets in per_student.items():
            student = student_map.get(student_id)
            students_rows.append(
                {
                    "student_id": student_id,
                    "student_display_name": student.student_name if student else "Unknown",
                    "buckets": {k: str(v.quantize(Decimal("0.01"))) for k, v in buckets.items()},
                }
            )

    summary = {
        "as_of": as_of_date.isoformat(),
        "currency": "USD",
        "totals": {k: str(v.quantize(Decimal("0.01"))) for k, v in totals.items()},
        "students": students_rows,
    }
    return summary
