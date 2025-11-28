"""Audit log model to track sensitive actions."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from backend.app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    acting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
