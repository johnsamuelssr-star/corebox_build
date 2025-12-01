"""Service to anonymize student data in a FERPA-safe way."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student


ANONYMIZED_SESSION_NOTES = "Content removed during anonymization"
ANONYMIZED_STUDENT_NAME = "Deleted Student"
ANONYMIZED_PARENT_NAME = "Deleted Guardian"


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
