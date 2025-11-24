from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class MonthlyRevenueRow(BaseModel):
    """Aggregated monthly revenue row for a tutor."""

    year: int
    month: int
    total_revenue: Decimal

    model_config = ConfigDict(from_attributes=True)
