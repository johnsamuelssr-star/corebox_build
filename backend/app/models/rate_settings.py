from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint

from backend.app.db.base_class import Base
from backend.app.core.time import utc_now


class RateSettings(Base):
    __tablename__ = "rate_settings"
    __table_args__ = (UniqueConstraint("owner_id", name="uq_rate_settings_owner"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hourly_rate = Column(Numeric(10, 2), nullable=False, default=Decimal("60.00"))
    half_hour_rate = Column(Numeric(10, 2), nullable=False, default=Decimal("40.00"))
    regular_rate_60 = Column(Numeric(10, 2), nullable=False, default=Decimal("60.00"))
    regular_rate_45 = Column(Numeric(10, 2), nullable=False, default=Decimal("45.00"))
    regular_rate_30 = Column(Numeric(10, 2), nullable=False, default=Decimal("30.00"))
    discount_rate_60 = Column(Numeric(10, 2), nullable=False, default=Decimal("60.00"))
    discount_rate_45 = Column(Numeric(10, 2), nullable=False, default=Decimal("45.00"))
    discount_rate_30 = Column(Numeric(10, 2), nullable=False, default=Decimal("30.00"))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
