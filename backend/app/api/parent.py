"""Parent-facing endpoints for linked students and reports."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.parent_link import ParentStudentLink
from backend.app.models.student import Student
from backend.app.schemas.parent import ParentStudentsList, ParentStudentSummary
from backend.app.schemas.admin_reporting import ParentReportWithNarrative
from backend.app.services.parent_report_narrative_service import get_parent_report_with_narrative

router = APIRouter(prefix="/parent", tags=["parent"])


def _get_linked_student(db: Session, parent_user_id: int, student_id: int) -> Student:
    link = (
        db.query(ParentStudentLink)
        .filter(
            ParentStudentLink.parent_user_id == parent_user_id,
            ParentStudentLink.student_id == student_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.get("/students", response_model=ParentStudentsList)
async def list_parent_students(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    links = db.query(ParentStudentLink).filter(ParentStudentLink.parent_user_id == current_user.id).all()
    student_ids = [lnk.student_id for lnk in links]
    students = db.query(Student).filter(Student.id.in_(student_ids)).all() if student_ids else []
    summaries = [
        ParentStudentSummary(
            student_id=stu.id,
            student_display_name=stu.student_name,
            parent_display_name=stu.parent_name,
        )
        for stu in students
    ]
    return {"students": summaries}


@router.get("/students/{student_id}/report", response_model=ParentReportWithNarrative)
async def parent_student_report(
    student_id: int,
    today: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = _get_linked_student(db, current_user.id, student_id)
    effective_today = today or datetime.now(timezone.utc).date()
    return get_parent_report_with_narrative(
        db=db,
        owner_id=student.owner_id,
        student_id=student.id,
        today=effective_today,
        start_date=start_date,
        end_date=end_date,
    )
