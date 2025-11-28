"""Login endpoint for CoreBox owners."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.email == credentials.email).first()
    if not owner or not verify_password(credentials.password, owner.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(user_id=owner.id)
    return {"access_token": token, "token_type": "bearer"}
