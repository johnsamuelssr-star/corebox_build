"""Invoice routes for tutors/owners."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.invoice import InvoiceRead, InvoiceUpdate
from backend.app.schemas.payment import PaymentCreate, PaymentRead
from backend.app.services.billing import create_invoice_for_student, determine_invoice_status, recalculate_invoice_totals
from backend.app.services.invoices import get_invoice_aging_summary

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _get_owned_student(db: Session, student_id: int, owner_id: int) -> Student:
    student = db.query(Student).filter(Student.id == student_id, Student.owner_id == owner_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.get("/aging-summary")
async def get_invoice_aging(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_invoice_aging_summary(db, current_user.id)


@router.get("/", response_model=List[InvoiceRead])
async def list_invoices(
    status: str | None = None,
    student_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice).filter(Invoice.owner_id == current_user.id)
    if status:
        query = query.filter(Invoice.status == status)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)

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


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.owner_id == current_user.id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/{student_id}/generate", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def generate_invoice_for_student(
    student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_student(db, student_id, current_user.id)
    invoice = create_invoice_for_student(db=db, owner_id=current_user.id, student_id=student_id)
    if invoice is None:
        raise HTTPException(status_code=400, detail="No billable sessions for this student")
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.owner_id == current_user.id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if payload.status is not None:
        invoice.status = payload.status
    if payload.due_date is not None:
        invoice.due_date = payload.due_date
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment_for_invoice(
    invoice_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.owner_id == current_user.id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status in ("void", "written_off"):
        raise HTTPException(status_code=400, detail="Cannot apply payment to a void or written-off invoice.")
    if payload.invoice_id != invoice_id:
        raise HTTPException(status_code=400, detail="Invoice ID mismatch")

    from decimal import Decimal

    existing_paid = sum((p.amount for p in invoice.payments if p.amount is not None), Decimal("0.00"))
    payment_amount = Decimal(str(payload.amount))

    received_at = payload.received_at or datetime.now(timezone.utc)
    payment = Payment(
        owner_id=current_user.id,
        invoice_id=invoice.id,
        amount=payment_amount,
        method=payload.method,
        notes=payload.notes,
        received_at=received_at,
    )
    db.add(payment)
    invoice.payments.append(payment)
    recalculate_invoice_totals(invoice)
    invoice.status = determine_invoice_status(invoice)
    db.commit()
    db.refresh(payment)
    db.refresh(invoice)
    return payment
