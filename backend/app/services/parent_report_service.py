"""Parent-friendly student report payload generation."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.services.student_analytics_reporting import get_student_analytics


def _compute_period_sessions(db: Session, student_id: int, owner_id: int, start_date: Optional[date], end_date: Optional[date]) -> tuple[int, Decimal]:
    query = db.query(SessionModel).filter(SessionModel.student_id == student_id, SessionModel.owner_id == owner_id)
    if start_date:
        query = query.filter(SessionModel.session_date >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
    if end_date:
        query = query.filter(SessionModel.session_date <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))
    sessions = query.all()
    count = len(sessions)
    minutes = sum((s.duration_minutes or 0) for s in sessions)
    hours = Decimal(minutes) / Decimal("60") if minutes else Decimal("0.00")
    return count, hours


def get_parent_report(
    db: Session,
    *,
    owner_id: int,
    student_id: int,
    today: date,
    start_date: Optional[date],
    end_date: Optional[date],
) -> dict:
    student = db.query(Student).filter(Student.id == student_id, Student.owner_id == owner_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    analytics = get_student_analytics(db, owner_id=owner_id, today=today)
    student_entry = next((s for s in analytics.get("students", []) if s.get("student_id") == student_id), None)
    if not student_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student analytics not found")

    kpis = student_entry["kpis"]
    weekly_activity = student_entry["weekly_activity_last_8_weeks"]

    total_hours_dec = Decimal(kpis["total_hours"])
    total_invoiced_dec = Decimal(kpis["total_invoiced"])

    if total_hours_dec > 0:
        nominal_rate_per_hour = (total_invoiced_dec / total_hours_dec).quantize(Decimal("0.01"))
    else:
        nominal_rate_per_hour = Decimal("0.00")

    # Period calculations
    if start_date:
        sessions_in_period, hours_in_period = _compute_period_sessions(db, student_id, owner_id, start_date, end_date)
    else:
        sessions_in_period = kpis["total_sessions"]
        hours_in_period = total_hours_dec

    report = {
        "as_of": today.isoformat(),
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "student": {
            "id": student.id,
            "display_name": student.student_name,
            "parent_display_name": student.parent_name,
            "contact_email": None,
            "contact_phone": None,
        },
        "progress_summary": {
            "total_sessions_all_time": kpis["total_sessions"],
            "total_hours_all_time": kpis["total_hours"],
            "sessions_in_period": sessions_in_period,
            "hours_in_period": str(Decimal(hours_in_period).quantize(Decimal("0.01"))),
            "consistency_score_0_100": kpis["consistency_score_0_100"],
            "current_session_streak_weeks": kpis["current_session_streak_weeks"],
            "last_session_date": kpis["last_session_date"],
            "first_session_date": kpis["first_session_date"],
        },
        "billing_summary": {
            "total_invoiced_all_time": kpis["total_invoiced"],
            "total_paid_all_time": kpis["total_paid"],
            "total_outstanding_all_time": kpis["total_outstanding"],
            "nominal_rate_per_hour": str(nominal_rate_per_hour),
            "billing_vs_usage_ratio": kpis["billing_vs_usage_ratio"],
        },
        "weekly_activity_last_8_weeks": weekly_activity,
        "notes_placeholders": {
            "academic_notes": "",
            "behavior_notes": "",
            "next_steps": "",
        },
    }
    return report
