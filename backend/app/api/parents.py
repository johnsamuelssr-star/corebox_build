"""Owner-facing parent listing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.app.dependencies.auth import get_current_user, get_db
from backend.app.models.parent_link import ParentStudentLink
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.parent import ParentContactRead, ParentCreate
from backend.app.schemas.student import StudentRead, StudentCreateForParent
from backend.app.services.parent_management_service import create_or_get_parent_user

router = APIRouter(prefix="/parents", tags=["parents"])


def _get_owned_parent_user(db: Session, parent_id: int, owner_id: int) -> User:
    parent_user = db.query(User).filter(User.id == parent_id, User.owner_id == owner_id).first()
    if parent_user:
        return parent_user

    parent_link = (
        db.query(ParentStudentLink)
        .join(Student, ParentStudentLink.student_id == Student.id)
        .filter(
            ParentStudentLink.parent_user_id == parent_id,
            Student.owner_id == owner_id,
        )
        .options(joinedload(ParentStudentLink.parent_user))
        .first()
    )
    parent_user = parent_link.parent_user if parent_link else None
    if parent_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")
    return parent_user


@router.get("/", response_model=list[ParentContactRead])
async def list_parents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all parent users linked to the current owner's students.
    """
    parents = db.query(User).filter(User.owner_id == current_user.id).all()
    if parents:
        return parents

    links = (
        db.query(ParentStudentLink)
        .join(Student, ParentStudentLink.student_id == Student.id)
        .filter(Student.owner_id == current_user.id)
        .options(joinedload(ParentStudentLink.parent_user))
        .all()
    )

    parents_by_id: dict[int, User] = {}
    for link in links:
        parent_user = getattr(link, "parent_user", None)
        if parent_user:
            parents_by_id[parent_user.id] = parent_user

    return list(parents_by_id.values())


@router.post("/", response_model=ParentContactRead, status_code=status.HTTP_201_CREATED)
async def create_parent(
    payload: ParentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent_user = create_or_get_parent_user(
        db=db,
        email=payload.email,
        password=None,
        owner_id=current_user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(parent_user)
    return parent_user


@router.get("/{parent_id}", response_model=ParentContactRead)
async def get_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_parent_user(db, parent_id, current_user.id)


@router.get("/{parent_id}/students", response_model=list[StudentRead])
async def get_parent_students(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_parent_user(db, parent_id, current_user.id)
    students = (
        db.query(Student)
        .join(ParentStudentLink, ParentStudentLink.student_id == Student.id)
        .filter(
            ParentStudentLink.parent_user_id == parent_id,
            Student.owner_id == current_user.id,
        )
        .all()
    )
    return students


@router.post("/{parent_id}/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
async def add_student_to_parent(
    parent_id: int,
    payload: StudentCreateForParent,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent_user = _get_owned_parent_user(db, parent_id, current_user.id)

    parent_full_name_parts = [parent_user.first_name, parent_user.last_name]
    parent_full_name = " ".join(part for part in parent_full_name_parts if part) or parent_user.full_name or "Parent"

    student = Student(
        owner_id=current_user.id,
        parent_name=parent_full_name,
        student_name=payload.student_name,
        grade_level=payload.grade_level,
        subject_focus=payload.subject_focus,
        status=payload.status or "active",
    )
    db.add(student)
    db.flush()

    db.add(
        ParentStudentLink(
            parent_user_id=parent_user.id,
            student_id=student.id,
            is_primary=True,
        )
    )

    db.commit()
    db.refresh(student)
    return student
