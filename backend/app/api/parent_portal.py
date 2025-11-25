"""Parent portal endpoints for linked students and reports."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_parent_user, get_db
from backend.app.schemas.admin_reporting import ParentMeStudentsResponse, ParentReportWithNarrative
from backend.app.services.parent_portal_service import (
    get_parent_student_report_with_narrative,
    get_parent_students_info,
)

router = APIRouter(prefix="/parent", tags=["parent-portal"])


@router.get("/me/students", response_model=ParentMeStudentsResponse)
async def list_my_students(
    db: Session = Depends(get_db),
    current_parent=Depends(get_current_parent_user),
):
    return get_parent_students_info(db=db, parent_user=current_parent)


@router.get("/students/{student_id}/report", response_model=ParentReportWithNarrative)
async def parent_student_report(
    student_id: int,
    today: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_parent=Depends(get_current_parent_user),
):
    effective_today = today or datetime.now(timezone.utc).date()
    report = get_parent_student_report_with_narrative(
        db=db,
        parent_user=current_parent,
        student_id=student_id,
        today=effective_today,
        start_date=start_date,
        end_date=end_date,
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found for this parent")
    return report
