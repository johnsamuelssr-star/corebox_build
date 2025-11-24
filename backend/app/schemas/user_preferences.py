"""User preferences schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserPreferencesBase(BaseModel):
    timezone: str = "UTC"
    default_session_length: Optional[int] = None
    weekly_schedule_notes: Optional[str] = None
    notifications_enabled: bool = True
    locale: str = "en-US"


class UserPreferencesUpdate(BaseModel):
    timezone: Optional[str] = None
    default_session_length: Optional[int] = None
    weekly_schedule_notes: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    locale: Optional[str] = None


class UserPreferencesRead(UserPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
