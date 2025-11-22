"""Lead schemas for create and read operations."""

from typing import Literal, Optional

from pydantic import BaseModel


AllowedLeadStatus = Literal["new", "contacted", "enrolled", "closed"]


class LeadBase(BaseModel):
    parent_name: str
    student_name: str
    grade_level: Optional[int] = None
    status: AllowedLeadStatus = "new"
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    """Schema for lead creation requests."""


class LeadRead(LeadBase):
    """Schema for lead responses."""

    id: int

    class Config:
        orm_mode = True
