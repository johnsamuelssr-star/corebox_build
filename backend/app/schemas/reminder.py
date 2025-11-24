"""Reminder schemas for lead follow-up tasks."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_serializer


class ReminderBase(BaseModel):
    title: str
    due_at: Optional[datetime] = None


class ReminderCreate(ReminderBase):
    """Schema for creating a reminder."""


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""

    title: Optional[str] = None
    due_at: Optional[datetime] = None
    completed: Optional[bool] = None


class ReminderRead(ReminderBase):
    """Schema for reading a reminder."""

    id: int
    lead_id: int
    title: str
    completed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None

    @field_validator("due_at", "created_at", "completed_at", mode="before")
    @classmethod
    def ensure_timezone(cls, v):
        if v is None:
            return v
        if isinstance(v, str) and v.endswith("Z"):
            return v[:-1] + "+00:00"
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        data = handler(self)
        for field in ["due_at", "created_at", "completed_at"]:
            v = data.get(field)
            if isinstance(v, datetime):
                iso = v.isoformat()
                if iso.endswith("Z"):
                    iso = iso.replace("Z", "+00:00")
                data[field] = iso
            elif isinstance(v, str) and v.endswith("Z"):
                data[field] = v.replace("Z", "+00:00")
        return data

    model_config = ConfigDict(from_attributes=True)
