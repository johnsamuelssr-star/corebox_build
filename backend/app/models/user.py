from sqlalchemy import Boolean, Column, DateTime, Integer, String, func, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base
from backend.app.models.student import Student


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    organization_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    leads = relationship("Lead", back_populates="owner")
    reminders = relationship("Reminder", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Reminder.owner_id")
    students = relationship(
        "Student",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys=[Student.owner_id],
    )
    sessions = relationship("Session", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Session.owner_id")
    rate_history = relationship("RateHistory", back_populates="owner", cascade="all, delete-orphan", foreign_keys="RateHistory.owner_id")
    preferences = relationship("UserPreferences", back_populates="user", cascade="all, delete-orphan", uselist=False)
    invoice_items = relationship("InvoiceItem", back_populates="owner", cascade="all, delete-orphan", foreign_keys="InvoiceItem.owner_id")
    invoice_templates = relationship("InvoiceTemplate", back_populates="owner", cascade="all, delete-orphan", foreign_keys="InvoiceTemplate.owner_id")
    invoices = relationship("Invoice", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Invoice.owner_id")
    payments = relationship("Payment", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Payment.owner_id")
    parent_links = relationship("ParentStudentLink", back_populates="parent_user", cascade="all, delete-orphan", foreign_keys="ParentStudentLink.parent_user_id")
