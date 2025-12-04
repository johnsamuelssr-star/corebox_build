"""Session model for CoreBox CRM."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base
from backend.app.core.time import utc_now


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    session_date = Column(DateTime, nullable=False)
    start_time = Column(Time, nullable=False)
    notes = Column(Text, nullable=True)
    rate_per_hour = Column(Numeric(10, 2), nullable=True)
    cost_total = Column(Numeric(10, 2), nullable=True)
    attendance = Column(String, nullable=False, default="present")
    session_type = Column(String, nullable=True)
    attendance_status = Column(String(20), nullable=False, default="scheduled")
    billing_status = Column(String(20), nullable=False, default="not_applicable")
    is_billable = Column(Boolean, nullable=False, default=True)
    rate_plan = Column(String(20), nullable=False, default="regular")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="sessions", foreign_keys=[owner_id])
    student = relationship("Student", back_populates="sessions", foreign_keys=[student_id])
    invoice_items = relationship("InvoiceItem", back_populates="session", cascade="all, delete-orphan")
