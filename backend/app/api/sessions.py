"""Session endpoints for CoreBox CRM."""

from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.rate_history import RateHistory
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.session import SessionCreate, SessionRead, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])


def calculate_cost_total(duration_minutes: int | None, rate_per_hour: float | Decimal | None) -> float | None:
    if duration_minutes is None or rate_per_hour is None:
        return None
    rate = float(rate_per_hour)
    if duration_minutes <= 0 or rate <= 0:
        return None
    hours = duration_minutes / 60.0
    return round(hours * rate, 2)


def _get_owned_student(db: Session, student_id: int, user_id: int) -> Student:
    student = db.query(Student).filter(Student.id == student_id, Student.owner_id == user_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


def _get_owned_session(db: Session, session_id: int, user_id: int) -> SessionModel:
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.owner_id == user_id).first()
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_obj


def _get_current_rate(db: Session, user_id: int) -> float:
    now = datetime.now(timezone.utc)
    rate = (
        db.query(RateHistory)
        .filter(RateHistory.owner_id == user_id, RateHistory.effective_at <= now)
        .order_by(RateHistory.effective_at.desc())
        .first()
    )
    if rate:
        return float(rate.rate_per_hour)
    return 60.0


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(session_in: SessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, session_in.student_id, current_user.id)
    rate_to_use = session_in.rate_per_hour if session_in.rate_per_hour is not None else _get_current_rate(db, current_user.id)
    cost_total = calculate_cost_total(session_in.duration_minutes, rate_to_use)
    session_obj = SessionModel(
        owner_id=current_user.id,
        student_id=student.id,
        subject=session_in.subject,
        duration_minutes=session_in.duration_minutes,
        session_date=session_in.session_date,
        start_time=session_in.start_time,
        notes=session_in.notes,
        rate_per_hour=rate_to_use,
        cost_total=cost_total,
        attendance=session_in.attendance or "present",
        session_type=session_in.session_type,
        attendance_status=session_in.attendance_status or "scheduled",
        billing_status=session_in.billing_status or "not_applicable",
        is_billable=session_in.is_billable if session_in.is_billable is not None else True,
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.get("/", response_model=list[SessionRead])
async def list_sessions(student_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(SessionModel).filter(SessionModel.owner_id == current_user.id)
    if student_id is not None:
        _get_owned_student(db, student_id, current_user.id)
        query = query.filter(SessionModel.student_id == student_id)
    query = query.order_by(SessionModel.session_date.desc(), SessionModel.created_at.desc())
    return query.all()


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_obj = _get_owned_session(db, session_id, current_user.id)
    return session_obj


@router.put("/{session_id}", response_model=SessionRead)
async def update_session(session_id: int, session_in: SessionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_obj = _get_owned_session(db, session_id, current_user.id)
    update_fields = {
        "subject": session_in.subject,
        "duration_minutes": session_in.duration_minutes,
        "session_date": session_in.session_date,
        "start_time": session_in.start_time,
        "notes": session_in.notes,
        "rate_per_hour": session_in.rate_per_hour,
        "attendance": session_in.attendance,
        "session_type": session_in.session_type,
        "attendance_status": session_in.attendance_status,
        "billing_status": session_in.billing_status,
        "is_billable": session_in.is_billable,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(session_obj, field, value)
    session_obj.cost_total = calculate_cost_total(session_obj.duration_minutes, session_obj.rate_per_hour)
    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.delete("/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_obj = _get_owned_session(db, session_id, current_user.id)
    db.delete(session_obj)
    db.commit()
    return {"status": "deleted", "id": session_id}
