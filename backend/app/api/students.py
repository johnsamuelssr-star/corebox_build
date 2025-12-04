"""Student endpoints for CoreBox CRM."""

from datetime import datetime, timezone
from decimal import Decimal

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.progress import StudentProgress, SubjectProgress
from backend.app.schemas.report import StudentReport
from backend.app.schemas.session import SessionRead
from backend.app.schemas.student import StudentAnonymizeResponse, StudentCreate, StudentRead, StudentUpdate
from backend.app.services.student_anonymization import anonymize_student

router = APIRouter(prefix="/students", tags=["students"])


class StudentSessionSummary(BaseModel):
    student_id: int
    total_sessions: int
    total_minutes: int
    total_hours: float
    total_earned: float


def _get_owned_student(db: Session, student_id: int, user_id: int) -> Student:
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.owner_id == user_id,
            Student.is_active.is_(True),
            Student.is_anonymized.is_(False),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


def _get_owned_lead(db: Session, lead_id: Optional[int], user_id: int) -> Lead | None:
    if lead_id is None:
        return None
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == user_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _attach_parent_metadata(student: Student) -> Student:
    parent_id = None
    rate_plan = "regular"
    primary_link = next((link for link in student.parent_links if getattr(link, "is_primary", False)), None)
    if primary_link is None and student.parent_links:
        primary_link = student.parent_links[0]
    parent_user = getattr(primary_link, "parent_user", None) if primary_link else None
    if parent_user:
        parent_id = parent_user.id
        rate_plan = parent_user.rate_plan or "regular"
    student.parent_id = parent_id
    student.parent_rate_plan = rate_plan
    return student


@router.post("/", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
async def create_student(student_in: StudentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if student_in.lead_id is not None:
        _get_owned_lead(db, student_in.lead_id, current_user.id)
    student = Student(
        owner_id=current_user.id,
        lead_id=student_in.lead_id,
        parent_name=student_in.parent_name,
        student_name=student_in.student_name,
        grade_level=student_in.grade_level,
        subject_focus=student_in.subject_focus,
        status=student_in.status or "active",
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    _attach_parent_metadata(student)
    return student


@router.get("/", response_model=list[StudentRead])
async def list_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    students = (
        db.query(Student)
        .filter(
            Student.owner_id == current_user.id,
            Student.is_active.is_(True),
            Student.is_anonymized.is_(False),
        )
        .all()
    )
    return [_attach_parent_metadata(stu) for stu in students]


@router.get("/{student_id}", response_model=StudentRead)
async def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    return _attach_parent_metadata(student)


@router.get("/{student_id}/sessions", response_model=list[SessionRead])
async def list_student_sessions(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.student_id == student.id, SessionModel.owner_id == current_user.id)
        .order_by(SessionModel.session_date.desc(), SessionModel.created_at.desc())
        .all()
    )
    return sessions


@router.get("/{student_id}/summary", response_model=StudentSessionSummary)
async def get_student_session_summary(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.student_id == student.id, SessionModel.owner_id == current_user.id)
        .all()
    )
    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)
    total_hours = round(total_minutes / 60.0, 2)
    total_earned_raw: float = 0.0
    for s in sessions:
        if s.cost_total is not None:
            total_earned_raw += float(s.cost_total)
    total_earned = round(total_earned_raw, 2)
    return StudentSessionSummary(
        student_id=student.id,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        total_hours=total_hours,
        total_earned=total_earned,
    )


@router.get("/{student_id}/report", response_model=StudentReport)
async def get_student_report(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.student_id == student.id, SessionModel.owner_id == current_user.id)
        .order_by(SessionModel.session_date.desc(), SessionModel.created_at.desc())
        .all()
    )
    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)
    raw_total_earned: float = 0.0
    for s in sessions:
        if s.cost_total is not None:
            raw_total_earned += float(s.cost_total)
    total_hours = round(total_minutes / 60.0, 2)
    total_earned = round(raw_total_earned, 2)

    if sessions:
        latest = sessions[0]
        oldest = sessions[-1]
        last_session_date = latest.session_date or latest.created_at
        first_session_date = oldest.session_date or oldest.created_at
    else:
        first_session_date = None
        last_session_date = None

    recent_sessions = sessions[:10]

    return StudentReport(
        student_id=student.id,
        parent_name=student.parent_name,
        student_name=student.student_name,
        grade_level=student.grade_level,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        total_hours=total_hours,
        total_earned=total_earned,
        first_session_date=first_session_date,
        last_session_date=last_session_date,
        recent_sessions=recent_sessions,
    )


@router.get("/{student_id}/progress", response_model=StudentProgress)
async def get_student_progress(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.student_id == student.id, SessionModel.owner_id == current_user.id)
        .all()
    )
    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)
    raw_total_earned: float = 0.0
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

    subject_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions_count": 0, "total_minutes": 0, "total_earned": 0.0}
    )
    for s in sessions:
        subject_key = s.subject or "Unspecified"
        entry = subject_map[subject_key]
        entry["sessions_count"] += 1
        entry["total_minutes"] += s.duration_minutes or 0
        if s.cost_total is not None:
            entry["total_earned"] += float(s.cost_total)

    subjects_progress: list[SubjectProgress] = []
    for subject, agg in subject_map.items():
        minutes = agg["total_minutes"]
        hours = round(minutes / 60.0, 2)
        earned = round(agg["total_earned"], 2)
        subjects_progress.append(
            SubjectProgress(
                subject=subject,
                sessions_count=agg["sessions_count"],
                total_minutes=minutes,
                total_hours=hours,
                total_earned=earned,
            )
        )

    return StudentProgress(
        student_id=student.id,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        total_hours=total_hours,
        total_earned=total_earned,
        average_minutes_per_session=average_minutes_per_session,
        average_earned_per_session=average_earned_per_session,
        subjects=subjects_progress,
    )


@router.put("/{student_id}", response_model=StudentRead)
async def update_student(student_id: int, student_in: StudentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, student_id, current_user.id)
    update_fields = {
        "parent_name": student_in.parent_name,
        "student_name": student_in.student_name,
        "grade_level": student_in.grade_level,
        "subject_focus": student_in.subject_focus,
        "status": student_in.status,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(student, field, value)
    db.commit()
    db.refresh(student)
    _attach_parent_metadata(student)
    return student


@router.delete("/{student_id}")
async def delete_student(
    student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    student = _get_owned_student(db, student_id, current_user.id)
    if student.is_anonymized:
        return {"status": "deleted", "id": student_id}

    student.is_active = False
    student.is_anonymized = True
    student.anonymized_at = datetime.now(timezone.utc)
    student.anonymized_by_id = current_user.id
    student.parent_name = "Deleted Guardian"
    student.student_name = "Deleted Student"
    student.status = "inactive"

    db.commit()
    return {"status": "deleted", "id": student_id}


@router.post("/{student_id}/anonymize", response_model=StudentAnonymizeResponse)
async def anonymize_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student, already_anonymized = anonymize_student(
        db,
        student_id=student_id,
        owner_id=current_user.id,
        acting_user_id=current_user.id,
    )
    return StudentAnonymizeResponse(student=student, already_anonymized=already_anonymized)
