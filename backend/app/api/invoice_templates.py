"""Invoice template endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.crud.crud_invoice_template import invoice_template_crud
from backend.app.models.user import User
from backend.app.schemas.invoice_template import (
    InvoiceTemplateCreate,
    InvoiceTemplateRead,
    InvoiceTemplateUpdate,
)

router = APIRouter(prefix="/invoice-templates", tags=["invoice_templates"])


@router.post("/", response_model=InvoiceTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_invoice_template(
    template_in: InvoiceTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return invoice_template_crud.create(db, obj_in=template_in, owner_id=current_user.id)


@router.get("/", response_model=list[InvoiceTemplateRead])
async def list_invoice_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return invoice_template_crud.get_multi(db, owner_id=current_user.id)


@router.get("/{template_id}", response_model=InvoiceTemplateRead)
async def get_invoice_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    template = invoice_template_crud.get(db, template_id=template_id, owner_id=current_user.id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")
    return template


@router.put("/{template_id}", response_model=InvoiceTemplateRead)
async def update_invoice_template(
    template_id: int,
    template_in: InvoiceTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = invoice_template_crud.get(db, template_id=template_id, owner_id=current_user.id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")
    return invoice_template_crud.update(db, db_obj=template, obj_in=template_in)


@router.delete("/{template_id}", response_model=InvoiceTemplateRead)
async def delete_invoice_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    template = invoice_template_crud.get(db, template_id=template_id, owner_id=current_user.id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")
    return invoice_template_crud.delete(db, db_obj=template)
