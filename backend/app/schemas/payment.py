"""Payment schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    amount: Decimal
    method: Optional[str] = None
    notes: Optional[str] = None
    received_at: Optional[datetime] = None


class PaymentCreate(PaymentBase):
    invoice_id: int


class PaymentRead(PaymentBase):
    id: int
    owner_id: int
    invoice_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
