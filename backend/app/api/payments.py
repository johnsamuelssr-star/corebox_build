"""Payment listing endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment
from backend.app.models.user import User
from backend.app.schemas.payment import PaymentRead

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=List[PaymentRead])
async def list_payments(
    invoice_id: int | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    method: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "received_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Payment)
        .join(Invoice)
        .filter(Payment.owner_id == current_user.id, Invoice.owner_id == current_user.id)
    )

    if invoice_id is not None:
        query = query.filter(Payment.invoice_id == invoice_id)
    if method:
        query = query.filter(Payment.method == method)
    if min_amount is not None:
        query = query.filter(Payment.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Payment.amount <= max_amount)
    if from_date is not None:
        query = query.filter(Payment.received_at >= from_date)
    if to_date is not None:
        query = query.filter(Payment.received_at <= to_date)

    supported_sort_fields = {
        "received_at": Payment.received_at,
        "amount": Payment.amount,
        "id": Payment.id,
    }
    if sort_by not in supported_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort_by field")
    sort_order_normalized = (sort_order or "desc").lower()
    if sort_order_normalized not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_order value")

    sort_column = supported_sort_fields[sort_by]
    if sort_order_normalized == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(skip).limit(limit)
    return query.all()
