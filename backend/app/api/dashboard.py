"""Dashboard overview endpoints."""

from collections import defaultdict
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.dashboard import DashboardOverview, StudentActivitySummary, SubjectSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_leads = db.query(Lead).filter(Lead.owner_id == current_user.id).count()
    total_students = db.query(Student).filter(Student.owner_id == current_user.id).count()

    sessions = db.query(SessionModel).filter(SessionModel.owner_id == current_user.id).all()

    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)

    raw_total_earned = 0.0
    for s in sessions:
        if s.cost_total is not None:
            raw_total_earned += float(s.cost_total)
    total_hours = round(total_minutes / 60.0, 2)
    total_earned = round(raw_total_earned, 2)

    if total_sessions > 0:
        average_minutes_per_session = round(total_minutes / total_sessions, 2)
        average_earned_per_session = round(total_earned / total_sessions, 2)
    else:
        average_minutes_per_session = 0.0
        average_earned_per_session = 0.0

    subject_map: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"sessions_count": 0, "total_minutes": 0, "total_earned": 0.0}
    )
    for s in sessions:
        subject_key = s.subject or "Unspecified"
        entry = subject_map[subject_key]
        entry["sessions_count"] += 1
        entry["total_minutes"] += s.duration_minutes or 0
        if s.cost_total is not None:
            entry["total_earned"] += float(s.cost_total)

    subjects: list[SubjectSummary] = []
    for subject, agg in subject_map.items():
        minutes = agg["total_minutes"]
        hours = round(minutes / 60.0, 2)
        earned = round(agg["total_earned"], 2)
        subjects.append(
            SubjectSummary(
                subject=subject,
                sessions_count=agg["sessions_count"],
                total_minutes=minutes,
                total_hours=hours,
                total_earned=earned,
            )
        )

    students_for_owner = db.query(Student).filter(Student.owner_id == current_user.id).all()
    student_name_by_id: Dict[int, str] = {s.id: s.student_name for s in students_for_owner}

    student_map: Dict[int, Dict[str, float]] = defaultdict(
        lambda: {"student_name": "", "total_sessions": 0, "total_minutes": 0, "total_earned": 0.0}
    )
    for s in sessions:
        if s.student_id is None:
            continue
        entry = student_map[s.student_id]
        if not entry["student_name"]:
            entry["student_name"] = student_name_by_id.get(s.student_id, "Unknown")
        entry["total_sessions"] += 1
        entry["total_minutes"] += s.duration_minutes or 0
        if s.cost_total is not None:
            entry["total_earned"] += float(s.cost_total)

    student_summaries: list[StudentActivitySummary] = []
    for student_id, agg in student_map.items():
        minutes = agg["total_minutes"]
        hours = round(minutes / 60.0, 2)
        earned = round(agg["total_earned"], 2)
        student_summaries.append(
            StudentActivitySummary(
                student_id=student_id,
                student_name=agg["student_name"],
                total_sessions=agg["total_sessions"],
                total_minutes=minutes,
                total_hours=hours,
                total_earned=earned,
            )
        )

    return DashboardOverview(
        total_leads=total_leads,
        total_students=total_students,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        total_hours=total_hours,
        total_earned=total_earned,
        average_minutes_per_session=average_minutes_per_session,
        average_earned_per_session=average_earned_per_session,
        subjects=subjects,
        students=student_summaries,
    )
