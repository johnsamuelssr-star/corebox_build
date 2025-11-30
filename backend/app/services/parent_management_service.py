from typing import List, Tuple, Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.models.parent_link import ParentStudentLink
from backend.app.models.student import Student
from backend.app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_or_get_parent_user(
    db: Session,
    email: str,
    password: Optional[str] = None,
    full_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
) -> User:
    """
    Idempotent-ish helper:
    - If a user with this email exists, return it.
    - Otherwise, create a new user with given credentials.
    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user

    hashed_password = get_password_hash(password) if password else None
    computed_full_name = full_name
    if not computed_full_name and (first_name or last_name):
        computed_full_name = " ".join(part for part in [first_name, last_name] if part) or None

    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=computed_full_name,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        bio=notes,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def link_parent_to_students(db: Session, parent_user: User, owner_id: int, students_payload: List[Tuple[int, bool]]):
    """
    Ensures links between parent_user and the given set of students.

    students_payload: list of (student_id, is_primary).
    Only students belonging to owner_id are valid.
    """
    student_ids = [sid for sid, _ in students_payload]
    if not student_ids:
        return

    students = (
        db.query(Student)
        .filter(Student.owner_id == owner_id, Student.id.in_(student_ids))
        .all()
    )
    existing_map = {
        (link.student_id, link.parent_user_id): link
        for link in parent_user.parent_links
    }

    for student in students:
        is_primary = next((is_pr for sid, is_pr in students_payload if sid == student.id), True)
        key = (student.id, parent_user.id)
        if key in existing_map:
            existing_map[key].is_primary = is_primary
        else:
            db.add(
                ParentStudentLink(
                    parent_user_id=parent_user.id,
                    student_id=student.id,
                    is_primary=is_primary,
                )
            )


def get_parent_students(db: Session, parent_user: User) -> list[Student]:
    """Convenience function to list a parent's linked students."""
    if not parent_user.parent_links:
        return []
    return [link.student for link in parent_user.parent_links]
