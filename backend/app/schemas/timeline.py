"""Timeline event schemas for lead activity."""

from datetime import datetime

from pydantic import BaseModel


class TimelineEventRead(BaseModel):
    id: int
    event_type: str
    description: str
    created_at: datetime

    class Config:
        orm_mode = True
