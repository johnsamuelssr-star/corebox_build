"""Owner dashboard data cards built from existing reporting services."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from backend.app.services.activity_reporting import get_activity_summary
from backend.app.services.aging_reporting import get_aging_summary
from backend.app.services.invoice_pipeline_reporting import get_invoice_pipeline_summary
from backend.app.services.payment_analytics_reporting import get_payment_analytics
from backend.app.services.reports import get_financial_summary_for_owner
from backend.app.services.student_analytics_reporting import get_student_analytics


def get_owner_dashboard_summary(db, *, owner_id: int, today: date) -> dict:
    # Financial card
    financial_all = get_financial_summary_for_owner(db, owner_id=owner_id)
    pay_analytics = get_payment_analytics(db, owner_id=owner_id, today=today)

    financial_card = {
        "total_invoiced_all_time": financial_all["total_invoiced"],
        "total_paid_all_time": financial_all["total_paid"],
        "total_outstanding_all_time": financial_all["total_outstanding"],
        "total_paid_last_30_days": pay_analytics["summary"]["total_paid_last_30_days"],
    }

    # Activity card
    activity_all = get_activity_summary(db, owner_id=owner_id)
    start_30 = today - timedelta(days=29)
    activity_30 = get_activity_summary(db, owner_id=owner_id, start_date=start_30)
    activity_card = {
        "total_sessions_all_time": activity_all["session_count"],
        "total_hours_all_time": activity_all["total_hours"],
        "sessions_last_30_days": activity_30["session_count"],
        "hours_last_30_days": activity_30["total_hours"],
    }

    # AR card
    aging = get_aging_summary(db, owner_id=owner_id)
    ar_totals = aging.get("totals", {})
    ar_card = {
        "current": ar_totals.get("current", "0.00"),
        "days_1_30": ar_totals.get("days_1_30", "0.00"),
        "days_31_60": ar_totals.get("days_31_60", "0.00"),
        "days_61_90": ar_totals.get("days_61_90", "0.00"),
        "days_90_plus": ar_totals.get("days_90_plus", "0.00"),
    }

    # Pipeline card
    pipeline = get_invoice_pipeline_summary(db, owner_id=owner_id, today=today)
    statuses = pipeline.get("statuses", {})
    due_windows = pipeline.get("due_windows", {})
    pipeline_card = {
        "draft_count": statuses.get("draft", {}).get("count", 0),
        "issued_count": statuses.get("issued", {}).get("count", 0),
        "partially_paid_count": statuses.get("partially_paid", {}).get("count", 0),
        "paid_count": statuses.get("paid", {}).get("count", 0),
        "past_due_count": due_windows.get("past_due", {}).get("count", 0),
        "upcoming_7_days_outstanding": due_windows.get("due_next_7_days", {}).get("total_outstanding", "0.00"),
    }

    return {
        "as_of": today.isoformat(),
        "financial": financial_card,
        "activity": activity_card,
        "ar": ar_card,
        "pipeline": pipeline_card,
    }


def get_student_dashboard_list(db, *, owner_id: int, today: date) -> dict:
    analytics = get_student_analytics(db, owner_id=owner_id, today=today)
    rows = []
    for stu in analytics.get("students", []):
        kpis = stu.get("kpis", {})
        rows.append(
            {
                "student_id": stu.get("student_id"),
                "student_display_name": stu.get("student_display_name"),
                "parent_display_name": stu.get("parent_display_name"),
                "total_sessions_all_time": kpis.get("total_sessions", 0),
                "total_hours_all_time": kpis.get("total_hours", "0.00"),
                "consistency_score_0_100": kpis.get("consistency_score_0_100", 0),
                "current_session_streak_weeks": kpis.get("current_session_streak_weeks", 0),
                "total_invoiced_all_time": kpis.get("total_invoiced", "0.00"),
                "total_paid_all_time": kpis.get("total_paid", "0.00"),
                "total_outstanding_all_time": kpis.get("total_outstanding", "0.00"),
            }
        )

    return {"as_of": today.isoformat(), "students": rows}
