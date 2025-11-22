"""Note schemas for lead notes."""

from datetime import datetime
from pydantic import BaseModel


class NoteBase(BaseModel):
    content: str


class NoteCreate(NoteBase):
    """Schema for creating a note."""


class NoteRead(NoteBase):
    """Schema for reading a note."""

    id: int
    lead_id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True
