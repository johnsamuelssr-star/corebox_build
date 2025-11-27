"""Invoice item model for billing entries."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String(255), nullable=True)
    rate_per_hour = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    cost_total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("invoice_templates.id"), nullable=True)

    session = relationship("Session", back_populates="invoice_items")
    student = relationship("Student", back_populates="invoice_items")
    owner = relationship("User", back_populates="invoice_items")
    invoice = relationship("Invoice", back_populates="items")
    template = relationship("InvoiceTemplate", back_populates="invoice_items")
