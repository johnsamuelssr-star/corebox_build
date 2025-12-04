from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RateSettingsBase(BaseModel):
    hourly_rate: Decimal
    half_hour_rate: Decimal
    regular_rate_60: Decimal
    regular_rate_45: Decimal
    regular_rate_30: Decimal
    discount_rate_60: Decimal
    discount_rate_45: Decimal
    discount_rate_30: Decimal


class RateSettingsRead(RateSettingsBase):
    model_config = ConfigDict(from_attributes=True)


class RateSettingsUpdate(BaseModel):
    hourly_rate: Decimal | None = None
    half_hour_rate: Decimal | None = None
    regular_rate_60: Decimal | None = None
    regular_rate_45: Decimal | None = None
    regular_rate_30: Decimal | None = None
    discount_rate_60: Decimal | None = None
    discount_rate_45: Decimal | None = None
    discount_rate_30: Decimal | None = None
