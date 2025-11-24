"""User preferences endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.user_preferences import UserPreferences
from backend.app.schemas.user_preferences import UserPreferencesRead, UserPreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _get_or_create_preferences(db: Session, user: User) -> UserPreferences:
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if prefs:
        return prefs
    prefs = UserPreferences(user_id=user.id)
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs


@router.get("/me", response_model=UserPreferencesRead)
async def get_my_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prefs = _get_or_create_preferences(db, current_user)
    return prefs


@router.put("/me", response_model=UserPreferencesRead)
async def update_my_preferences(
    update: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = _get_or_create_preferences(db, current_user)
    update_fields = {
        "timezone": update.timezone,
        "default_session_length": update.default_session_length,
        "weekly_schedule_notes": update.weekly_schedule_notes,
        "notifications_enabled": update.notifications_enabled,
        "locale": update.locale,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs
