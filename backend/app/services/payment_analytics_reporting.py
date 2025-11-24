"""Payment analytics and cash flow reporting."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from backend.app.models.payment import Payment


def _week_start_end(iso_year: int, iso_week: int) -> Tuple[date, date]:
    # ISO weeks start on Monday
    first_day = datetime.strptime(f"{iso_year} {iso_week} 1", "%G %V %u").date()
    return first_day, first_day + timedelta(days=6)


def _last_n_iso_weeks(today: date, n: int = 8) -> List[Tuple[int, int]]:
    # returns list from oldest to newest
    current_year, current_week, _ = today.isocalendar()
    weeks = []
    year, week = current_year, current_week
    for _ in range(n):
        weeks.append((year, week))
        week -= 1
        if week == 0:
            year -= 1
            week = date(year, 12, 28).isocalendar()[1]
    return list(reversed(weeks))


def _last_n_months(today: date, n: int = 12) -> List[Tuple[int, int]]:
    # returns list from oldest to newest
    year = today.year
    month = today.month
    months = []
    for _ in range(n):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


def get_payment_analytics(db: Session, *, owner_id: int, today: date | None = None) -> dict:
    as_of_date = today or datetime.now(timezone.utc).date()

    payments: List[Payment] = db.query(Payment).filter(Payment.owner_id == owner_id).all()

    total_paid_all_time = sum((Decimal(str(p.amount or 0)) for p in payments), Decimal("0.00"))
    payment_count_all_time = len(payments)
    average_payment_amount_all_time = (
        (total_paid_all_time / payment_count_all_time).quantize(Decimal("0.01"))
        if payment_count_all_time > 0
        else Decimal("0.00")
    )

    last_7_start = as_of_date - timedelta(days=6)
    last_30_start = as_of_date - timedelta(days=29)
    total_paid_last_7_days = sum(
        (Decimal(str(p.amount or 0)) for p in payments if p.created_at.date() >= last_7_start), Decimal("0.00")
    )
    total_paid_last_30_days = sum(
        (Decimal(str(p.amount or 0)) for p in payments if p.created_at.date() >= last_30_start), Decimal("0.00")
    )

    week_keys = _last_n_iso_weeks(as_of_date, 8)
    week_map = {key: {"total_paid": Decimal("0.00"), "payment_count": 0} for key in week_keys}
    for p in payments:
        py, pw, _ = p.created_at.date().isocalendar()
        key = (py, pw)
        if key in week_map:
            week_map[key]["total_paid"] += Decimal(str(p.amount or 0))
            week_map[key]["payment_count"] += 1
    weekly_trend = []
    for year, week in week_keys:
        start_d, end_d = _week_start_end(year, week)
        weekly_trend.append(
            {
                "year": year,
                "iso_week": week,
                "start_date": start_d.isoformat(),
                "end_date": end_d.isoformat(),
                "total_paid": str(week_map[(year, week)]["total_paid"].quantize(Decimal("0.01"))),
                "payment_count": week_map[(year, week)]["payment_count"],
            }
        )

    month_keys = _last_n_months(as_of_date, 12)
    month_map = {key: {"total_paid": Decimal("0.00"), "payment_count": 0} for key in month_keys}
    for p in payments:
        key = (p.created_at.date().year, p.created_at.date().month)
        if key in month_map:
            month_map[key]["total_paid"] += Decimal(str(p.amount or 0))
            month_map[key]["payment_count"] += 1
    monthly_trend = []
    for year, month in month_keys:
        monthly_trend.append(
            {
                "year": year,
                "month": month,
                "total_paid": str(month_map[(year, month)]["total_paid"].quantize(Decimal("0.01"))),
                "payment_count": month_map[(year, month)]["payment_count"],
            }
        )

    methods_map: Dict[str, Dict[str, Decimal | int]] = {}
    for p in payments:
        method = p.method or "unspecified"
        entry = methods_map.setdefault(method, {"total_paid": Decimal("0.00"), "payment_count": 0})
        entry["total_paid"] += Decimal(str(p.amount or 0))
        entry["payment_count"] += 1
    methods = [
        {
            "method": method,
            "total_paid": str(vals["total_paid"].quantize(Decimal("0.01"))),
            "payment_count": vals["payment_count"],
        }
        for method, vals in methods_map.items()
    ]

    analytics = {
        "as_of": as_of_date.isoformat(),
        "currency": "USD",
        "summary": {
            "total_paid_all_time": str(total_paid_all_time.quantize(Decimal("0.01"))),
            "total_paid_last_7_days": str(total_paid_last_7_days.quantize(Decimal("0.01"))),
            "total_paid_last_30_days": str(total_paid_last_30_days.quantize(Decimal("0.01"))),
            "payment_count_all_time": payment_count_all_time,
            "average_payment_amount_all_time": str(average_payment_amount_all_time.quantize(Decimal("0.01"))),
        },
        "weekly_trend": weekly_trend,
        "monthly_trend": monthly_trend,
        "methods": methods,
    }
    return analytics
