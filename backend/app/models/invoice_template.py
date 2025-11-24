"""Invoice template model for reusable billing presets."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    default_rate = Column(Numeric(10, 2), nullable=True)
    default_description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="invoice_templates")
    invoice_items = relationship("InvoiceItem", back_populates="template", cascade="all, delete-orphan")
