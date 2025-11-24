"""Timeline event schemas for lead activity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimelineEventRead(BaseModel):
    id: int
    event_type: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
