"""Rate history endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.rate_history import RateHistory
from backend.app.models.user import User
from backend.app.schemas.rate_history import RateHistoryCreate, RateHistoryRead

router = APIRouter(prefix="/rates", tags=["rates"])


@router.post("/", response_model=RateHistoryRead, status_code=status.HTTP_201_CREATED)
async def create_rate(rate_in: RateHistoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rate = RateHistory(
        owner_id=current_user.id,
        rate_per_hour=rate_in.rate_per_hour,
        effective_at=rate_in.effective_at,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/", response_model=list[RateHistoryRead])
async def list_rates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(RateHistory)
        .filter(RateHistory.owner_id == current_user.id)
        .order_by(RateHistory.effective_at.desc())
        .all()
    )


@router.get("/current")
async def get_current_rate(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    rate = (
        db.query(RateHistory)
        .filter(RateHistory.owner_id == current_user.id, RateHistory.effective_at <= now)
        .order_by(RateHistory.effective_at.desc())
        .first()
    )
    if rate:
        return {"rate_per_hour": float(rate.rate_per_hour)}
    return {"rate_per_hour": 60.0}
