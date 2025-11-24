"""Invoice template schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceTemplateBase(BaseModel):
    name: str
    default_rate: Optional[float] = None
    default_description: Optional[str] = None


class InvoiceTemplateCreate(InvoiceTemplateBase):
    pass


class InvoiceTemplateUpdate(BaseModel):
    name: Optional[str] = None
    default_rate: Optional[float] = None
    default_description: Optional[str] = None


class InvoiceTemplateRead(InvoiceTemplateBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
