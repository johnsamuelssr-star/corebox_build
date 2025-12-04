from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.schemas.student import StudentCreate, StudentRead


class FamilyEnrollmentParentCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    notes: Optional[str] = None
    rate_plan: Optional[str] = "regular"


class FamilyEnrollmentParentRead(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = Field(default=None, alias="bio")
    rate_plan: Optional[str] = "regular"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FamilyEnrollmentStudentCreate(StudentCreate):
    pass


class FamilyEnrollmentCreate(BaseModel):
    parent: FamilyEnrollmentParentCreate
    students: list[FamilyEnrollmentStudentCreate]


class FamilyEnrollmentResponse(BaseModel):
    parent: FamilyEnrollmentParentRead
    students: list[StudentRead]

    model_config = ConfigDict(from_attributes=True)
