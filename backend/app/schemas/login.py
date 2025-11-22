"""Login request schema for user authentication."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Payload for login attempts."""

    email: EmailStr
    password: str
