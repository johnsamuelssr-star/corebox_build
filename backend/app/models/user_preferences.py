"""User preferences model for CoreBox CRM."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.app.core.time import utc_now
from backend.app.db.base import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    timezone = Column(String, nullable=False, default="UTC")
    default_session_length = Column(Integer, nullable=True)
    weekly_schedule_notes = Column(String, nullable=True)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    locale = Column(String, nullable=False, default="en-US")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="preferences")
