"""Authentication dependencies for retrieving the current user."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.user import User


def get_current_user(db: Session = Depends(get_db), authorization: str | None = Header(default=None)) -> User:
    # Expect Authorization: Bearer <token>
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        # Decode and validate JWT to retrieve subject
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
