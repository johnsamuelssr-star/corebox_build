"""Lead model for CoreBox CRM."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    parent_name = Column(String, nullable=False)
    student_name = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="new")
    notes = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="leads")
