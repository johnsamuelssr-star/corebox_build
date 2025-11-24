"""Reporting helpers for tutor revenue."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment
from backend.app.models.user import User
from backend.app.schemas.reports import MonthlyRevenueRow


def get_monthly_revenue_for_user(
    db: Session,
    user: User,
    from_date: date | None = None,
    to_date: date | None = None,
) -> List[MonthlyRevenueRow]:
    """Aggregate monthly revenue for the given tutor based on payments."""

    year_col = func.extract("year", Payment.created_at)
    month_col = func.extract("month", Payment.created_at)

    query = (
        db.query(
            year_col.label("year"),
            month_col.label("month"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
        )
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.owner_id == user.id)
    )

    if from_date is not None:
        query = query.filter(func.date(Payment.created_at) >= from_date)
    if to_date is not None:
        query = query.filter(func.date(Payment.created_at) <= to_date)

    results = (
        query.group_by(year_col, month_col)
        .order_by(year_col.desc(), month_col.desc())
        .all()
    )

    rows: List[MonthlyRevenueRow] = []
    for row in results:
        rows.append(
            MonthlyRevenueRow(
                year=int(row.year),
                month=int(row.month),
                total_revenue=Decimal(row.total_revenue),
            )
        )
    return rows


def get_financial_summary_for_owner(
    db: Session,
    owner_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Return aggregate invoice/payment totals for an owner within an optional date range."""
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
    paid_invoice_count = sum(1 for inv in invoices if (inv.balance_due or Decimal("0")) <= 0)
    unpaid_invoice_count = len(invoices) - paid_invoice_count

    total_paid = Decimal("0.00")
    if invoice_ids:
        pay_query = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.invoice_id.in_(invoice_ids))
        total_paid = Decimal(str(pay_query.scalar() or 0))

    summary = {
        "total_invoiced": str(Decimal(total_invoiced).quantize(Decimal("0.01"))),
        "total_paid": str(Decimal(total_paid).quantize(Decimal("0.01"))),
        "total_outstanding": str(Decimal(total_outstanding).quantize(Decimal("0.01"))),
        "invoice_count": len(invoices),
        "paid_invoice_count": paid_invoice_count,
        "unpaid_invoice_count": unpaid_invoice_count,
    }
    return summary
