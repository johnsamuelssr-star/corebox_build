"""Session schemas for CoreBox CRM."""

from datetime import datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class SessionBase(BaseModel):
    subject: str
    duration_minutes: int
    session_date: datetime
    start_time: time
    notes: Optional[str] = None
    rate_per_hour: Optional[float] = None
    cost_total: Optional[float] = None
    attendance: Optional[Literal["present", "absent", "no_show", "cancelled"]] = "present"
    session_type: Optional[Literal["online", "in_person"]] = None
    attendance_status: Optional[Literal["scheduled", "completed", "cancelled", "no_show"]] = None
    billing_status: Optional[Literal["not_applicable", "pending", "invoiced", "paid"]] = None
    is_billable: Optional[bool] = None


class SessionCreate(SessionBase):
    student_id: int


class SessionUpdate(BaseModel):
    subject: Optional[str] = None
    duration_minutes: Optional[int] = None
    session_date: Optional[datetime] = None
    start_time: Optional[time] = None
    notes: Optional[str] = None
    rate_per_hour: Optional[float] = None
    cost_total: Optional[float] = None
    attendance: Optional[Literal["present", "absent", "no_show", "cancelled"]] = None
    session_type: Optional[Literal["online", "in_person"]] = None
    attendance_status: Optional[Literal["scheduled", "completed", "cancelled", "no_show"]] = None
    billing_status: Optional[Literal["not_applicable", "pending", "invoiced", "paid"]] = None
    is_billable: Optional[bool] = None


class SessionRead(SessionBase):
    id: int
    student_id: int
    owner_id: int
    cost_total: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    attendance_status: str
    billing_status: str
    is_billable: bool

    model_config = ConfigDict(from_attributes=True)
