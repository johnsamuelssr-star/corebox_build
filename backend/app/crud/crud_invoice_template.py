"""CRUD operations for invoice templates."""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.models.invoice_template import InvoiceTemplate
from backend.app.schemas.invoice_template import InvoiceTemplateCreate, InvoiceTemplateUpdate


class CRUDInvoiceTemplate:
    def create(self, db: Session, *, obj_in: InvoiceTemplateCreate, owner_id: int) -> InvoiceTemplate:
        obj = InvoiceTemplate(owner_id=owner_id, **obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, *, template_id: int, owner_id: int) -> Optional[InvoiceTemplate]:
        return (
            db.query(InvoiceTemplate)
            .filter(InvoiceTemplate.id == template_id, InvoiceTemplate.owner_id == owner_id)
            .first()
        )

    def get_multi(self, db: Session, *, owner_id: int) -> List[InvoiceTemplate]:
        return (
            db.query(InvoiceTemplate)
            .filter(InvoiceTemplate.owner_id == owner_id)
            .order_by(InvoiceTemplate.created_at.desc())
            .all()
        )

    def update(self, db: Session, *, db_obj: InvoiceTemplate, obj_in: InvoiceTemplateUpdate) -> InvoiceTemplate:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, db_obj: InvoiceTemplate) -> InvoiceTemplate:
        db.delete(db_obj)
        db.commit()
        return db_obj


invoice_template_crud = CRUDInvoiceTemplate()
