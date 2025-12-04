from pydantic import BaseModel, ConfigDict


class ParentStudentSummary(BaseModel):
    student_id: int
    student_display_name: str
    parent_display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class ParentStudentsList(BaseModel):
    students: list[ParentStudentSummary]

    model_config = ConfigDict(from_attributes=True)


class ParentContactRead(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    full_name: str | None = None
    bio: str | None = None
    rate_plan: str | None = "regular"

    model_config = ConfigDict(from_attributes=True)


class ParentCreate(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    notes: str | None = None
    rate_plan: str | None = "regular"


class ParentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    notes: str | None = None
    rate_plan: str | None = None
