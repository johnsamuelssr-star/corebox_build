"""Lead timeline endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.timeline import TimelineEvent
from backend.app.models.user import User
from backend.app.schemas.timeline import TimelineEventRead

router = APIRouter(prefix="/leads", tags=["timeline"])


def _get_owned_lead(db: Session, lead_id: int, user_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == user_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/{lead_id}/timeline", response_model=list[TimelineEventRead])
async def get_timeline(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_lead(db, lead_id, current_user.id)
    return (
        db.query(TimelineEvent)
        .filter(TimelineEvent.lead_id == lead_id, TimelineEvent.owner_id == current_user.id)
        .order_by(TimelineEvent.created_at.asc(), TimelineEvent.id.asc())
        .all()
    )
