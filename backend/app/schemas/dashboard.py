"""Dashboard schemas for owner-level overviews."""

from typing import List

from pydantic import BaseModel, ConfigDict


class SubjectSummary(BaseModel):
    subject: str
    sessions_count: int
    total_minutes: int
    total_hours: float
    total_earned: float

    model_config = ConfigDict(from_attributes=True)


class StudentActivitySummary(BaseModel):
    student_id: int
    student_name: str
    total_sessions: int
    total_minutes: int
    total_hours: float
    total_earned: float

    model_config = ConfigDict(from_attributes=True)


class DashboardOverview(BaseModel):
    total_leads: int
    total_students: int
    total_sessions: int
    total_minutes: int
    total_hours: float
    total_earned: float
    average_minutes_per_session: float
    average_earned_per_session: float
    subjects: List[SubjectSummary]
    students: List[StudentActivitySummary]

    model_config = ConfigDict(from_attributes=True)
