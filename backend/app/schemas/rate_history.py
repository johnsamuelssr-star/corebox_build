"""Rate history schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RateHistoryBase(BaseModel):
    rate_per_hour: float
    effective_at: datetime


class RateHistoryCreate(RateHistoryBase):
    pass


class RateHistoryRead(RateHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
