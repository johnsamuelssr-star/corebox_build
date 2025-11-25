"""Dashboard endpoints for owner-level summary cards and student list."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.schemas.admin_reporting import OwnerDashboardSummary, StudentDashboardList
from backend.app.services.dashboard_service import get_owner_dashboard_summary, get_student_dashboard_list

router = APIRouter(prefix="/admin/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=OwnerDashboardSummary)
async def get_owner_dashboard_summary_endpoint(
    today: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Owner dashboard summary cards."""
    effective_today = today or datetime.now(timezone.utc).date()
    return get_owner_dashboard_summary(db=db, owner_id=current_user.id, today=effective_today)


@router.get("/students", response_model=StudentDashboardList)
async def get_student_dashboard_list_endpoint(
    today: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Per-student dashboard rows for the current owner."""
    effective_today = today or datetime.now(timezone.utc).date()
    return get_student_dashboard_list(db=db, owner_id=current_user.id, today=effective_today)
