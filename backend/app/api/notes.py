"""Lead notes endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.note import Note
from backend.app.models.user import User
from backend.app.schemas.note import NoteCreate, NoteRead
from backend.app.services.timeline import log_event

router = APIRouter(prefix="/leads", tags=["leads"])


def _get_owned_lead(db: Session, lead_id: int, user_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == user_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/notes", response_model=NoteRead)
async def create_note(
    lead_id: int,
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_owned_lead(db, lead_id, current_user.id)
    note = Note(lead_id=lead.id, owner_id=current_user.id, content=note_in.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    log_event(db, lead.id, current_user.id, "note_added", f"Note added: {note.content[:40]}")
    return note


@router.get("/{lead_id}/notes", response_model=list[NoteRead])
async def list_notes(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_lead(db, lead_id, current_user.id)
    return (
        db.query(Note)
        .filter(Note.lead_id == lead_id, Note.owner_id == current_user.id)
        .order_by(Note.created_at.asc())
        .all()
    )
