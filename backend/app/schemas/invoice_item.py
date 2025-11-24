"""Invoice item schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceItemBase(BaseModel):
    description: Optional[str] = None
    rate_per_hour: Decimal | float
    duration_minutes: int


class InvoiceItemCreate(InvoiceItemBase):
    session_id: int
    student_id: Optional[int] = None
    template_id: Optional[int] = None


class InvoiceItemRead(InvoiceItemBase):
    id: int
    session_id: int
    student_id: Optional[int] = None
    owner_id: int
    cost_total: Decimal | float
    created_at: datetime
    template_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
