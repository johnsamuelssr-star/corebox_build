from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.auth import get_current_user, get_db
from backend.app.models.rate_settings import RateSettings
from backend.app.models.user import User
from backend.app.schemas.rate_settings import RateSettingsRead, RateSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_HOURLY = Decimal("60.00")
DEFAULT_HALF_HOUR = Decimal("40.00")
DEFAULT_RATE_60 = Decimal("60.00")
DEFAULT_RATE_45 = Decimal("45.00")
DEFAULT_RATE_30 = Decimal("30.00")


def _ensure_owner_access(user: User):
    if getattr(user, "is_admin", False):
        return
    # Owners created via /auth/register have owner_id None. Parent-linked users have owner_id set.
    if user.owner_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage settings")


def _get_or_create_rate_settings(db: Session, owner_id: int) -> RateSettings:
    settings = db.query(RateSettings).filter(RateSettings.owner_id == owner_id).first()
    if settings:
        return settings
    settings = RateSettings(
        owner_id=owner_id,
        hourly_rate=DEFAULT_HOURLY,
        half_hour_rate=DEFAULT_HALF_HOUR,
        regular_rate_60=DEFAULT_RATE_60,
        regular_rate_45=DEFAULT_RATE_45,
        regular_rate_30=DEFAULT_RATE_30,
        discount_rate_60=DEFAULT_RATE_60,
        discount_rate_45=DEFAULT_RATE_45,
        discount_rate_30=DEFAULT_RATE_30,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/rates", response_model=RateSettingsRead)
async def get_rate_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_owner_access(current_user)
    settings = _get_or_create_rate_settings(db, current_user.id)
    return settings


@router.put("/rates", response_model=RateSettingsRead)
async def update_rate_settings(
    payload: RateSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_owner_access(current_user)
    settings = _get_or_create_rate_settings(db, current_user.id)
    if payload.hourly_rate is not None:
        settings.hourly_rate = payload.hourly_rate
    if payload.half_hour_rate is not None:
        settings.half_hour_rate = payload.half_hour_rate
    if payload.regular_rate_60 is not None:
        settings.regular_rate_60 = payload.regular_rate_60
    if payload.regular_rate_45 is not None:
        settings.regular_rate_45 = payload.regular_rate_45
    if payload.regular_rate_30 is not None:
        settings.regular_rate_30 = payload.regular_rate_30
    if payload.discount_rate_60 is not None:
        settings.discount_rate_60 = payload.discount_rate_60
    if payload.discount_rate_45 is not None:
        settings.discount_rate_45 = payload.discount_rate_45
    if payload.discount_rate_30 is not None:
        settings.discount_rate_30 = payload.discount_rate_30
    db.commit()
    db.refresh(settings)
    return settings
