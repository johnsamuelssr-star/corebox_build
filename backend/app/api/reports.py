"""Reporting endpoints for tutor revenue."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.reports import MonthlyRevenueRow
from backend.app.services.reports import get_monthly_revenue_for_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly-revenue", response_model=List[MonthlyRevenueRow])
async def get_monthly_revenue(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_monthly_revenue_for_user(db, current_user, from_date, to_date)
