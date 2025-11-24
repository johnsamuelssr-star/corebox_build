"""Invoice-related service helpers."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice


def _init_bucket():
    return {"count": 0, "total_balance": Decimal("0.00")}


def get_invoice_aging_summary(db: Session, owner_id: int) -> dict:
    """Compute aging buckets for a tutor's open invoices."""
    now = datetime.now(timezone.utc)
    today = now.date()

    buckets = {
        "current": _init_bucket(),
        "days_1_30": _init_bucket(),
        "days_31_60": _init_bucket(),
        "days_61_90": _init_bucket(),
        "days_90_plus": _init_bucket(),
    }

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.owner_id == owner_id,
            Invoice.balance_due > Decimal("0.00"),
            Invoice.status.notin_(["paid", "void", "written_off"]),
        )
        .all()
    )

    for invoice in invoices:
        balance = Decimal(str(invoice.balance_due or 0)).quantize(Decimal("0.01"))
        due_date = invoice.due_date.date() if invoice.due_date else None
        if due_date is None or due_date >= today:
            bucket_key = "current"
        else:
            days_past_due = (today - due_date).days
            if 1 <= days_past_due <= 30:
                bucket_key = "days_1_30"
            elif 31 <= days_past_due <= 60:
                bucket_key = "days_31_60"
            elif 61 <= days_past_due <= 90:
                bucket_key = "days_61_90"
            else:
                bucket_key = "days_90_plus"

        bucket = buckets[bucket_key]
        bucket["count"] += 1
        bucket["total_balance"] += balance

    # Format totals to strings for response consistency
    formatted_buckets = {}
    for key, data in buckets.items():
        formatted_buckets[key] = {
            "count": data["count"],
            "total_balance": str(data["total_balance"].quantize(Decimal("0.01"))),
        }

    return {"as_of": now.isoformat(), "buckets": formatted_buckets}
