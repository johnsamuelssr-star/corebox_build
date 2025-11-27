"""Student schemas for CoreBox CRM."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class StudentBase(BaseModel):
    parent_name: str
    student_name: str
    grade_level: Optional[int] = None
    subject_focus: Optional[str] = None
    status: Optional[str] = "active"


class StudentCreate(StudentBase):
    lead_id: Optional[int] = None


class StudentUpdate(BaseModel):
    parent_name: Optional[str] = None
    student_name: Optional[str] = None
    grade_level: Optional[int] = None
    subject_focus: Optional[str] = None
    status: Optional[str] = None


class StudentRead(StudentBase):
    id: int
    lead_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerStudentSummary(BaseModel):
    id: int
    firstName: str
    lastName: str
    status: Literal["active", "inactive"]
    gradeLevel: Optional[str] = None
    subjectFocus: Optional[str] = None
    parentName: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
