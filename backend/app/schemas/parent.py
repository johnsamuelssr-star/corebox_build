from pydantic import BaseModel, ConfigDict


class ParentStudentSummary(BaseModel):
    student_id: int
    student_display_name: str
    parent_display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class ParentStudentsList(BaseModel):
    students: list[ParentStudentSummary]

    model_config = ConfigDict(from_attributes=True)
