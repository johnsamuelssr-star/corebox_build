"""User schemas used for registration and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    organization_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileRead(UserProfileBase):
    id: int
    email: EmailStr
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserRead(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AdminUserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
