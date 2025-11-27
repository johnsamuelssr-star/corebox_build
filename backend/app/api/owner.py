"""Owner-level endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.parent_link import ParentStudentLink
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.student import OwnerStudentSummary

router = APIRouter(prefix="/owner", tags=["owner"])


def _split_student_name(student_name: str | None) -> tuple[str, str]:
    if not student_name:
        return "", ""
    parts = student_name.split()
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first, last


def _build_parent_name(student: Student) -> str | None:
    primary_link = next((link for link in student.parent_links if link.is_primary), None)
    if primary_link is None and student.parent_links:
        primary_link = student.parent_links[0]
    if not primary_link or not getattr(primary_link, "parent_user", None):
        return None
    parent_user = primary_link.parent_user
    parts = [getattr(parent_user, "first_name", None), getattr(parent_user, "last_name", None)]
    combined = " ".join(part for part in parts if part)
    return combined or None


@router.get("/students", response_model=list[OwnerStudentSummary])
async def get_owner_students(
    current_owner: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    students = (
        db.query(Student)
        .options(joinedload(Student.parent_links).joinedload(ParentStudentLink.parent_user))
        .filter(Student.owner_id == current_owner.id)
        .all()
    )

    summaries: list[OwnerStudentSummary] = []
    for student in students:
        first_name, last_name = _split_student_name(student.student_name)
        parent_name = _build_parent_name(student)
        status_value = "active" if (student.status or "").lower() == "active" else "inactive"
        summaries.append(
            OwnerStudentSummary(
                id=student.id,
                firstName=first_name,
                lastName=last_name,
                status=status_value,
                gradeLevel=str(student.grade_level) if student.grade_level is not None else None,
                subjectFocus=student.subject_focus,
                parentName=parent_name,
            )
        )

    return summaries
