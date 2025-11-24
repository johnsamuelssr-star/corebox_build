"""Progress schemas for student analytics."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SubjectProgress(BaseModel):
    subject: str
    sessions_count: int
    total_minutes: int
    total_hours: float
    total_earned: float

    model_config = ConfigDict(from_attributes=True)


class StudentProgress(BaseModel):
    student_id: int
    total_sessions: int
    total_minutes: int
    total_hours: float
    total_earned: float
    average_minutes_per_session: float
    average_earned_per_session: float
    subjects: List[SubjectProgress]

    model_config = ConfigDict(from_attributes=True)
