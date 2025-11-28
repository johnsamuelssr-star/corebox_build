"""Service to anonymize student data in a FERPA-safe way."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student
from backend.app.models.user import User


ANONYMIZED_STUDENT_NAME = "Deleted Student"
ANONYMIZED_PARENT_NAME = "Deleted Guardian"
ANONYMIZED_SESSION_NOTES = "Content removed during anonymization"


def _anonymize_parent_users(student: Student) -> None:
    for link in getattr(student, "parent_links", []) or []:
        parent_user = getattr(link, "parent_user", None)
        if not parent_user or not isinstance(parent_user, User):
            continue
        parent_user.first_name = None
        parent_user.last_name = None
        parent_user.full_name = None
        parent_user.phone = None
        parent_user.organization_name = None
        parent_user.avatar_url = None
        parent_user.bio = None
        parent_user.email = f"deleted-parent-{parent_user.id}@example.com"
        parent_user.is_active = False


def anonymize_student(db: Session, *, student_id: int, owner_id: int, acting_user_id: int) -> tuple[Student, bool]:
    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.owner_id == owner_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    already_anonymized = bool(student.is_anonymized)
    if already_anonymized:
        return student, True

    now = datetime.now(timezone.utc)

    student.is_active = False
    student.status = "inactive"
    student.is_anonymized = True
    student.anonymized_at = now
    student.anonymized_by_id = acting_user_id

    student.student_name = ANONYMIZED_STUDENT_NAME
    student.parent_name = ANONYMIZED_PARENT_NAME
    student.grade_level = None
    student.subject_focus = None

    _anonymize_parent_users(student)

    for session_obj in student.sessions:
        session_obj.notes = ANONYMIZED_SESSION_NOTES

    audit_entry = AuditLog(
        owner_id=owner_id,
        acting_user_id=acting_user_id,
        student_id=student.id,
        action="student_anonymized",
        created_at=now,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(student)
    return student, False
