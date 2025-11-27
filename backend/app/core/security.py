"""Security utilities for CoreBox CRM: password hashing and JWT token operations.

Handles JWT creation with subject and expiration claims and validates tokens with
consistent error handling.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=True)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_minutes: Optional[int] = None) -> str:
    settings = get_settings()
    user_identifier = (
        user_id.get("sub") if isinstance(user_id, dict) and "sub" in user_id else user_id
    )
    expire_delta = timedelta(minutes=expires_minutes if expires_minutes is not None else getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    expire = datetime.now(timezone.utc) + expire_delta
    # Embed expiration claim so tokens self-expire when validated
    payload = {"sub": str(user_identifier), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Expired token") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc


def _get_db():
    # Local import to avoid circular dependency at module import time
    from backend.app.db.session import get_db

    yield from get_db()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(_get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
