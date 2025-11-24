"""Report schemas for student overviews."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.session import SessionRead


class StudentReport(BaseModel):
    student_id: int
    parent_name: str
    student_name: str
    grade_level: Optional[int] = None

    total_sessions: int
    total_minutes: int
    total_hours: float
    total_earned: float

    first_session_date: Optional[datetime] = None
    last_session_date: Optional[datetime] = None

    recent_sessions: List[SessionRead]

    model_config = ConfigDict(from_attributes=True)
