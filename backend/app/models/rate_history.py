"""Rate history model for tutor rates over time."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from backend.app.core.time import utc_now
from backend.app.db.base_class import Base


class RateHistory(Base):
    __tablename__ = "rate_history"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rate_per_hour = Column(Numeric(10, 2), nullable=False)
    effective_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="rate_history")
