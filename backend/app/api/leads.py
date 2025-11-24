"""Lead management endpoints."""

from datetime import datetime, timezone

from sqlalchemy import or_

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.lead import Lead
from backend.app.models.user import User
from backend.app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from backend.app.services.timeline import log_event

router = APIRouter(prefix="/leads", tags=["leads"])

ALLOWED_TRANSITIONS = {
    "new": {"contacted", "closed_lost"},
    "contacted": {"trial_scheduled", "closed_lost"},
    "trial_scheduled": {"enrolled", "closed_lost"},
    "enrolled": {"closed_lost"},
    "closed_lost": set(),
}


def validate_status_transition(current_status: str, new_status: str) -> bool:
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    return new_status in allowed


def _get_owned_lead(db: Session, lead_id: int, user_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == user_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


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
    log_event(db, lead.id, current_user.id, "lead_created", "Lead created")
    return lead


@router.get("/", response_model=list[LeadRead])
async def list_leads(
    status: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str | None = "created_at",
    sort_order: str | None = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Lead).filter(Lead.owner_id == current_user.id)
    if status:
        query = query.filter(Lead.status == status)
    if search:
        tokens = [t for t in search.split() if t]
        for token in tokens:
            pattern = f"%{token}%"
            token_clause = or_(
                Lead.parent_name.ilike(pattern),
                Lead.student_name.ilike(pattern),
                Lead.notes.ilike(pattern),
            )
            query = query.filter(token_clause)
    supported_sort_fields = {
        "created_at": Lead.created_at,
        "status": Lead.status,
        "grade_level": Lead.grade_level,
        "status_changed_at": Lead.status_changed_at,
    }
    sort_field = sort_by or "created_at"
    if sort_field not in supported_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort_by value")
    sort_column = supported_sort_fields[sort_field]

    sort_order_normalized = (sort_order or "desc").lower()
    if sort_order_normalized not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_order value")

    if sort_order_normalized == "asc":
        order_by_clause = [sort_column.asc(), Lead.id.asc()]
    else:
        order_by_clause = [sort_column.desc(), Lead.id.desc()]

    query = query.order_by(*order_by_clause)
    query = query.offset(skip).limit(limit)
    return query.all()


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lead = _get_owned_lead(db, lead_id, current_user.id)
    return lead


@router.put("/{lead_id}", response_model=LeadRead)
async def update_lead(lead_id: int, lead_in: LeadUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lead = _get_owned_lead(db, lead_id, current_user.id)
    changed_fields: list[str] = []
    old_status = lead.status
    update_fields = {
        "parent_name": lead_in.parent_name,
        "student_name": lead_in.student_name,
        "grade_level": lead_in.grade_level,
        "notes": lead_in.notes,
    }
    if lead_in.status is not None and lead_in.status != lead.status:
        if not validate_status_transition(lead.status, lead_in.status):
            raise HTTPException(status_code=400, detail="Invalid status transition")
        lead.status = lead_in.status
        lead.status_changed_at = datetime.now(timezone.utc)
        changed_fields.append("status")

    for field, value in update_fields.items():
        if value is not None:  # Only update provided fields
            current_value = getattr(lead, field)
            if current_value != value:
                setattr(lead, field, value)
                changed_fields.append(field)
    db.commit()
    db.refresh(lead)
    if "status" in changed_fields:
        log_event(db, lead.id, current_user.id, "status_changed", f"Status changed from {old_status} to {lead.status}")
    non_status_changes = [f for f in changed_fields if f != "status"]
    if non_status_changes:
        description = "Lead updated: " + "; ".join(f"{f} changed" for f in non_status_changes)
        log_event(db, lead.id, current_user.id, "lead_updated", description)
    return lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lead = _get_owned_lead(db, lead_id, current_user.id)
    log_event(db, lead.id, current_user.id, "lead_deleted", "Lead deleted")
    db.delete(lead)
    db.commit()
    return {"status": "deleted", "id": lead_id}
