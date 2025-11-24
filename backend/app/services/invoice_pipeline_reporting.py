"""Invoice pipeline reporting for owners."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice


STATUS_KEYS = ["draft", "issued", "paid", "partially_paid", "void"]


def _init_status_buckets() -> Dict[str, dict]:
    return {
        key: {"count": 0, "total_amount": Decimal("0.00"), "total_outstanding": Decimal("0.00")}
        for key in STATUS_KEYS
    }


def _init_due_windows() -> Dict[str, dict]:
    return {
        "past_due": {"count": 0, "total_outstanding": Decimal("0.00")},
        "due_next_7_days": {"count": 0, "total_outstanding": Decimal("0.00")},
        "due_next_30_days": {"count": 0, "total_outstanding": Decimal("0.00")},
    }


def _map_status(status: str) -> str:
    if status == "draft":
        return "draft"
    if status == "paid":
        return "paid"
    if status == "partial":
        return "partially_paid"
    if status == "void":
        return "void"
    return "issued"


def get_invoice_pipeline_summary(
    db: Session,
    *,
    owner_id: int,
    today: date | None = None,
) -> dict:
    as_of_date = today or datetime.now(timezone.utc).date()
    invoices = db.query(Invoice).filter(Invoice.owner_id == owner_id).all()

    statuses = _init_status_buckets()
    due_windows = _init_due_windows()

    total_invoiced = Decimal("0.00")
    total_outstanding = Decimal("0.00")
    invoice_count = 0

    for inv in invoices:
        status_key = _map_status(inv.status or "issued")
        total_amount = Decimal(str(inv.total_amount or 0)).quantize(Decimal("0.01"))
        outstanding = Decimal(str(inv.balance_due or 0)).quantize(Decimal("0.01"))

        bucket = statuses[status_key]
        bucket["count"] += 1
        bucket["total_amount"] += total_amount
        bucket["total_outstanding"] += outstanding

        if status_key != "void":
            total_invoiced += total_amount
            total_outstanding += outstanding
            invoice_count += 1

        # Due windows: consider only outstanding, non-void invoices
        if status_key != "void" and outstanding > 0:
            due_date = inv.due_date.date() if inv.due_date else None
            if due_date is None:
                continue
            days_from_today = (due_date - as_of_date).days
            if days_from_today < 0:
                win = "past_due"
            elif days_from_today <= 7:
                win = "due_next_7_days"
            elif days_from_today <= 30:
                win = "due_next_30_days"
            else:
                win = None
            if win:
                due_windows[win]["count"] += 1
                due_windows[win]["total_outstanding"] += outstanding

    summary = {
        "as_of": as_of_date.isoformat(),
        "currency": "USD",
        "summary": {
            "total_invoiced": str(total_invoiced.quantize(Decimal("0.01"))),
            "total_outstanding": str(total_outstanding.quantize(Decimal("0.01"))),
            "invoice_count": invoice_count,
        },
        "statuses": {
            key: {
                "count": data["count"],
                "total_amount": str(data["total_amount"].quantize(Decimal("0.01"))),
                "total_outstanding": str(data["total_outstanding"].quantize(Decimal("0.01"))),
            }
            for key, data in statuses.items()
        },
        "due_windows": {
            key: {
                "count": data["count"],
                "total_outstanding": str(data["total_outstanding"].quantize(Decimal("0.01"))),
            }
            for key, data in due_windows.items()
        },
    }
    return summary
