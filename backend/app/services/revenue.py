"""Revenue calculation helpers."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment


def get_ytd_revenue_for_owner(db: Session, owner_id: int) -> Decimal:
    """Return calendar year-to-date revenue for a tutor based on payments."""
    now = datetime.now(timezone.utc)
    start_of_year = datetime(now.year, 1, 1, tzinfo=timezone.utc)

    total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.owner_id == owner_id, Payment.created_at >= start_of_year)
        .scalar()
    )

    # Ensure a Decimal is always returned
    return Decimal(str(total or 0)).quantize(Decimal("0.01"))
