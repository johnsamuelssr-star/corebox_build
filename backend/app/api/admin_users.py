"""Admin user management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_admin
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import AdminUserRead, AdminUserStatusUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[AdminUserRead])
async def list_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(User).order_by(User.id.asc()).all()


@router.get("/{user_id}", response_model=AdminUserRead)
async def get_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return _get_user(db, user_id)


@router.patch("/{user_id}/status", response_model=AdminUserRead)
async def update_user_status(
    user_id: int,
    update: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = _get_user(db, user_id)
    if user_id == current_admin.id and update.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    if user_id == current_admin.id and update.is_admin is not None and update.is_admin != current_admin.is_admin:
        raise HTTPException(status_code=400, detail="Cannot change your own admin flag")

    if update.is_active is not None:
        user.is_active = update.is_active
    if update.is_admin is not None:
        user.is_admin = update.is_admin
    db.commit()
    db.refresh(user)
    return user
