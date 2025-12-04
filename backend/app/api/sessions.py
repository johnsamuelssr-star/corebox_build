"""Session endpoints for CoreBox CRM."""

from decimal import Decimal
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.rate_history import RateHistory
from backend.app.models.rate_settings import RateSettings
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


def _get_rate_settings(db: Session, owner_id: int) -> RateSettings | None:
    settings = db.query(RateSettings).filter(RateSettings.owner_id == owner_id).first()
    if settings:
        return settings
    settings = RateSettings(owner_id=owner_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _select_rate(settings: RateSettings | None, plan: str, duration_minutes: int) -> float:
    if settings is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session rates are not configured.")

    if duration_minutes not in (30, 45, 60):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported session duration. Allowed durations are 30, 45, or 60 minutes.",
        )

    plan_key = plan or "regular"
    rate_lookup = {
        ("regular", 60): settings.regular_rate_60,
        ("regular", 45): settings.regular_rate_45,
        ("regular", 30): settings.regular_rate_30,
        ("discount", 60): settings.discount_rate_60,
        ("discount", 45): settings.discount_rate_45,
        ("discount", 30): settings.discount_rate_30,
    }

    rate_value = rate_lookup.get((plan_key, duration_minutes))
    if rate_value is None or float(rate_value) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rate for this duration and plan is not configured. Please set it in Session Rates.",
        )
    return float(rate_value)


def _serialize_session(session_obj: SessionModel, current_user: User) -> dict:
    data = SessionRead.model_validate(session_obj).model_dump()
    privileged = bool(
        getattr(current_user, "is_admin", False)
        or session_obj.owner_id == current_user.id
        or getattr(current_user, "parent_links", None)
    )
    if not privileged:
        data.pop("cost_total", None)
    data["rate_plan"] = data.get("rate_plan") or getattr(session_obj, "rate_plan", None) or "regular"
    return data


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(session_in: SessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _get_owned_student(db, session_in.student_id, current_user.id)
    settings = _get_rate_settings(db, current_user.id)
    parent_user = student.parent_links[0].parent_user if getattr(student, "parent_links", None) else None
    plan = getattr(parent_user, "rate_plan", None) or "regular"

    selected_rate = _select_rate(settings, plan, session_in.duration_minutes)
    rate_to_use = session_in.rate_per_hour if session_in.rate_per_hour is not None else selected_rate
    cost_total = selected_rate
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
        rate_plan=plan,
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return _serialize_session(session_obj, current_user)


@router.get("/", response_model=list[SessionRead])
async def list_sessions(
    student_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    tutor_id: int | None = None,  # placeholder for future tutor support
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(SessionModel).filter(SessionModel.owner_id == current_user.id)
    if student_id is not None:
        _get_owned_student(db, student_id, current_user.id)
        query = query.filter(SessionModel.student_id == student_id)
    if start_date is not None:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.filter(SessionModel.session_date >= start_dt)
    if end_date is not None:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.filter(SessionModel.session_date <= end_dt)
    query = query.order_by(SessionModel.session_date.desc(), SessionModel.created_at.desc())
    sessions = query.all()
    return [_serialize_session(sess, current_user) for sess in sessions]


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_obj = _get_owned_session(db, session_id, current_user.id)
    return _serialize_session(session_obj, current_user)


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
        "cost_total": session_in.cost_total,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(session_obj, field, value)
    session_obj.cost_total = calculate_cost_total(session_obj.duration_minutes, session_obj.rate_per_hour)
    db.commit()
    db.refresh(session_obj)
    return _serialize_session(session_obj, current_user)


@router.delete("/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_obj = _get_owned_session(db, session_id, current_user.id)
    db.delete(session_obj)
    db.commit()
    return {"status": "deleted", "id": session_id}
