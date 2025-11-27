"""Lead model for CoreBox CRM."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base
from backend.app.core.time import utc_now


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    parent_name = Column(String, nullable=False)
    student_name = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="new")
    status_changed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="leads")
    lead_notes = relationship("Note", back_populates="lead", cascade="all, delete-orphan")
    timeline = relationship("TimelineEvent", back_populates="lead", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="lead", cascade="all, delete-orphan")
    student = relationship("Student", back_populates="lead", uselist=False)
