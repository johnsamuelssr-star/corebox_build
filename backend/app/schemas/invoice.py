"""Invoice schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceBase(BaseModel):
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    student_id: int

    status: str
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    due_date: Optional[datetime]

    created_at: datetime
    updated_at: datetime
