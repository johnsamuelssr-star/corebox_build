"""Handles user registration for the CoreBox CRM."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api import auth  # ensures router package export
from backend.app.core.security import get_password_hash
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine, get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserRead

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user_in.password)  # Hash password before storing
    user = User(email=user_in.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
