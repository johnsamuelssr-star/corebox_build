"""Revenue endpoints."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.services.revenue import get_ytd_revenue_for_owner

router = APIRouter(prefix="/revenue", tags=["revenue"])


@router.get("/ytd")
async def get_ytd_revenue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ytd_total = get_ytd_revenue_for_owner(db, current_user.id)
    now_year = datetime.now(timezone.utc).year
    # Ensure two-decimal string formatting for consistency across money fields
    formatted_total = Decimal(ytd_total).quantize(Decimal("0.01"))
    return {"year": now_year, "ytd_revenue": str(formatted_total)}
