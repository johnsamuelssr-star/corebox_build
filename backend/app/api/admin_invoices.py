"""Admin invoice endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_admin
from backend.app.db.session import get_db
from backend.app.models.invoice import Invoice
from backend.app.models.user import User
from backend.app.schemas.invoice import InvoiceRead

router = APIRouter(prefix="/admin/invoices", tags=["admin-invoices"])


@router.get("/", response_model=List[InvoiceRead])
async def list_all_invoices(
    owner_id: int | None = None,
    student_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Invoice)
    if owner_id is not None:
        query = query.filter(Invoice.owner_id == owner_id)
    if student_id is not None:
        query = query.filter(Invoice.student_id == student_id)
    if status is not None:
        query = query.filter(Invoice.status == status)

    supported_sort_fields = {
        "created_at": Invoice.created_at,
        "status": Invoice.status,
        "total_amount": Invoice.total_amount,
        "due_date": Invoice.due_date,
    }
    if sort_by not in supported_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort_by value")
    sort_order_normalized = (sort_order or "desc").lower()
    if sort_order_normalized not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_order value")
    sort_column = supported_sort_fields[sort_by]
    if sort_order_normalized == "asc":
        order_by_clause = [sort_column.asc(), Invoice.id.asc()]
    else:
        order_by_clause = [sort_column.desc(), Invoice.id.desc()]

    query = query.order_by(*order_by_clause).offset(skip).limit(limit)
    return query.all()
