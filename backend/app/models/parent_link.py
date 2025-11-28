"""Parent-student link model for parent portal access."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id = Column(Integer, primary_key=True, index=True)
    parent_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("parent_user_id", "student_id", name="uq_parent_student_link"),
    )

    parent_user = relationship("User", back_populates="parent_links", foreign_keys=[parent_user_id])
    student = relationship("Student", back_populates="parent_links", foreign_keys=[student_id])
