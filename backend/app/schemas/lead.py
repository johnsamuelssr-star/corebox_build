"""Lead schemas for create and read operations."""

from typing import Literal, Optional

from pydantic import BaseModel


AllowedLeadStatus = Literal["new", "contacted", "trial_scheduled", "enrolled", "closed_lost"]


class LeadBase(BaseModel):
    parent_name: str
    student_name: str
    grade_level: Optional[int] = None
    status: AllowedLeadStatus = "new"
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    """Schema for lead creation requests."""


class LeadUpdate(BaseModel):
    """Schema for lead updates with partial fields."""

    parent_name: Optional[str] = None
    student_name: Optional[str] = None
    grade_level: Optional[int] = None
    status: Optional[AllowedLeadStatus] = None
    notes: Optional[str] = None


class LeadRead(LeadBase):
    """Schema for lead responses."""

    id: int

    class Config:
        orm_mode = True
