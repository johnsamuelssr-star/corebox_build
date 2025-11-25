"""Admin endpoints for managing parent accounts and links."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.schemas.admin_reporting import ParentAccountCreate
from backend.app.services.parent_management_service import (
    create_or_get_parent_user,
    link_parent_to_students,
)

router = APIRouter(prefix="/admin/parents", tags=["admin-parents"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_or_link_parent(
    payload: ParentAccountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    parent_user = create_or_get_parent_user(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    students_payload = [(link.student_id, link.is_primary) for link in payload.students]
    link_parent_to_students(
        db=db,
        parent_user=parent_user,
        owner_id=current_user.id,
        students_payload=students_payload,
    )
    db.commit()
    return {"parent_user_id": parent_user.id}
