from datetime import date

from sqlalchemy.orm import Session

from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.admin_reporting import (
    ParentMeStudentsResponse,
    ParentStudentInfo,
    ParentReportWithNarrative,
)
from backend.app.services.parent_report_narrative_service import get_parent_report_with_narrative


def get_parent_students_info(db: Session, parent_user: User) -> ParentMeStudentsResponse:
    """Return students linked to the parent."""
    result: list[ParentStudentInfo] = []

    for link in parent_user.parent_links:
        student: Student = link.student
        display_name = getattr(student, "student_name", None) or getattr(student, "full_name", "")
        result.append(
            ParentStudentInfo(
                student_id=student.id,
                student_display_name=display_name,
                owner_id=student.owner_id,
            )
        )

    return ParentMeStudentsResponse(students=result)


def get_parent_student_report_with_narrative(
    db: Session,
    *,
    parent_user: User,
    student_id: int,
    today: date,
    start_date: date | None,
    end_date: date | None,
) -> ParentReportWithNarrative | None:
    """Return narrative parent report for a linked student, or None if not linked."""
    link = next((link for link in parent_user.parent_links if link.student_id == student_id), None)
    if not link:
        return None

    student = link.student
    owner = student.owner if hasattr(student, "owner") else None
    if owner is None:
        owner = db.query(User).filter(User.id == student.owner_id).first()
    if owner is None:
        return None

    report = get_parent_report_with_narrative(
        db=db,
        owner_id=owner.id if hasattr(owner, "id") else owner,
        student_id=student.id,
        today=today,
        start_date=start_date,
        end_date=end_date,
    )
    return report
