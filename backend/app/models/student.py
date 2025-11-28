"""Student model for CoreBox CRM."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base
from backend.app.core.time import utc_now


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, unique=True)
    parent_name = Column(String, nullable=False)
    student_name = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=True)
    subject_focus = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    is_active = Column(Boolean, nullable=False, default=True)
    is_anonymized = Column(Boolean, nullable=False, default=False)
    anonymized_at = Column(DateTime, nullable=True)
    anonymized_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="students", foreign_keys=[owner_id])
    anonymized_by = relationship("User", foreign_keys=[anonymized_by_id])
    lead = relationship("Lead", back_populates="student", uselist=False)
    sessions = relationship("Session", back_populates="student", cascade="all, delete-orphan", foreign_keys="Session.student_id")
    invoice_items = relationship("InvoiceItem", back_populates="student", foreign_keys="InvoiceItem.student_id")
    invoices = relationship("Invoice", back_populates="student", cascade="all, delete-orphan", foreign_keys="Invoice.student_id")
    parent_links = relationship("ParentStudentLink", back_populates="student", cascade="all, delete-orphan", foreign_keys="ParentStudentLink.student_id")
