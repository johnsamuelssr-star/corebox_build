from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user, get_db
from backend.app.models.lead import Lead
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.enrollment import FamilyEnrollmentCreate, FamilyEnrollmentResponse
from backend.app.services.parent_management_service import create_or_get_parent_user, link_parent_to_students

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


def _get_owned_lead(db: Session, lead_id: int | None, owner_id: int) -> Lead | None:
    if lead_id is None:
        return None
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == owner_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("/family", response_model=FamilyEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_family_enrollment(
    enrollment: FamilyEnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not enrollment.students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one student is required for enrollment.",
        )

    try:
        parent_user = create_or_get_parent_user(
            db=db,
            email=enrollment.parent.email,
            password=None,
            owner_id=current_user.id,
            first_name=enrollment.parent.first_name,
            last_name=enrollment.parent.last_name,
            phone=enrollment.parent.phone,
            notes=enrollment.parent.notes,
        )

        created_students: list[Student] = []
        for student_in in enrollment.students:
            if student_in.lead_id is not None:
                _get_owned_lead(db, student_in.lead_id, current_user.id)
            student = Student(
                owner_id=current_user.id,
                lead_id=student_in.lead_id,
                parent_name=student_in.parent_name,
                student_name=student_in.student_name,
                grade_level=student_in.grade_level,
                subject_focus=student_in.subject_focus,
                status=student_in.status or "active",
            )
            db.add(student)
            created_students.append(student)

        db.flush()

        link_parent_to_students(
            db=db,
            parent_user=parent_user,
            owner_id=current_user.id,
            students_payload=[(stu.id, True) for stu in created_students],
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(parent_user)
    for student in created_students:
        db.refresh(student)

    return FamilyEnrollmentResponse(parent=parent_user, students=created_students)
