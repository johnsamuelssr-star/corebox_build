"""Reminder endpoints for follow-up tasks on leads."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.reminder import Reminder
from backend.app.models.user import User
from backend.app.schemas.reminder import ReminderCreate, ReminderRead, ReminderUpdate
from backend.app.services.timeline import log_event

router = APIRouter(prefix="/reminders", tags=["reminders"])


def _get_owned_lead(db: Session, lead_id: int, user_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == user_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _get_owned_reminder(db: Session, reminder_id: int, user_id: int) -> Reminder:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.owner_id == user_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.post("/leads/{lead_id}/reminders", response_model=ReminderRead, status_code=201)
async def create_reminder(
    lead_id: int,
    reminder_in: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_owned_lead(db, lead_id, current_user.id)
    reminder = Reminder(
        lead_id=lead.id,
        owner_id=current_user.id,
        title=reminder_in.title,
        due_at=reminder_in.due_at,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    log_event(db, lead.id, current_user.id, "reminder_created", f"Reminder created: {reminder.title}")
    return reminder


@router.get("/leads/{lead_id}/reminders", response_model=list[ReminderRead])
async def list_reminders(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_lead(db, lead_id, current_user.id)
    return (
        db.query(Reminder)
        .filter(Reminder.lead_id == lead_id, Reminder.owner_id == current_user.id)
        .order_by(Reminder.due_at.is_(None), Reminder.due_at.asc(), Reminder.created_at.asc())
        .all()
    )


@router.put("/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: int,
    reminder_in: ReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = _get_owned_reminder(db, reminder_id, current_user.id)
    if reminder_in.title is not None:
        reminder.title = reminder_in.title
    if reminder_in.due_at is not None:
        reminder.due_at = reminder_in.due_at
    if reminder_in.completed is not None and reminder_in.completed != reminder.completed:
        reminder.completed = reminder_in.completed
        if reminder.completed:
            if reminder.completed_at is None:
                reminder.completed_at = datetime.now(timezone.utc)
            log_event(db, reminder.lead_id, current_user.id, "reminder_completed", f"Reminder completed: {reminder.title}")
        else:
            reminder.completed_at = None
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = _get_owned_reminder(db, reminder_id, current_user.id)
    lead_id = reminder.lead_id
    db.delete(reminder)
    db.commit()
    log_event(db, lead_id, current_user.id, "reminder_deleted", f"Reminder deleted: {reminder_id}")
    return {"status": "deleted", "id": reminder_id}
