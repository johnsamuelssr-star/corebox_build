"""Protected routes that require authentication."""

from fastapi import APIRouter, Depends

from backend.app.dependencies.auth import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/protected", tags=["protected"])


@router.get("/ping")
async def protected_ping(current_user: User = Depends(get_current_user)):
    return {"status": "ok", "user_id": current_user.id}
