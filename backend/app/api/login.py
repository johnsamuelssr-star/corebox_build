"""Handles user login and token generation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token, verify_password
from backend.app.dependencies.auth import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.login import LoginRequest
from backend.app.schemas.token import AccessToken
from backend.app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AccessToken)
def login_user(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(credentials.password, user.hashed_password):  # Verify password securely
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(user_id=user.id)  # Issue JWT for authenticated user
    return AccessToken(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Returns the current authenticated user."""
    return UserRead(id=current_user.id, email=current_user.email)
