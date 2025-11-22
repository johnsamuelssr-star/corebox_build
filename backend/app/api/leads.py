"""Lead management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.user import User
from backend.app.schemas.lead import LeadCreate, LeadRead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadRead)
async def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lead = Lead(
        parent_name=lead_in.parent_name,
        student_name=lead_in.student_name,
        grade_level=lead_in.grade_level,
        status=lead_in.status,
        notes=lead_in.notes,
        owner_id=current_user.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=list[LeadRead])
async def list_leads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Lead).filter(Lead.owner_id == current_user.id).all()
