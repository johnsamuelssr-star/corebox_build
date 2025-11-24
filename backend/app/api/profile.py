"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserProfileRead)
async def get_my_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/me", response_model=UserProfileRead)
async def update_my_profile(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    update_fields = {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "phone": profile.phone,
        "organization_name": profile.organization_name,
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
