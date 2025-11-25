"""Generate parent report with narrative overlays."""

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.services.parent_report_service import get_parent_report


def _attendance_phrase(consistency: int, streak: int) -> str:
    if consistency >= 80:
        base = "Attendance has been strong and consistent over the last several weeks."
    elif consistency >= 50:
        base = "Attendance has been generally solid, with a few gaps."
    else:
        base = "Attendance has been inconsistent, with multiple missed or skipped weeks."

    if streak >= 3:
        tail = " There is a positive streak of recent weekly attendance."
    elif streak == 0:
        tail = " There has been at least one week recently with no sessions."
    else:
        tail = ""
    return base + tail


def _academic_progress_phrase(student_name: str, sessions_in_period: int, hours_in_period: str) -> str:
    if sessions_in_period == 0:
        return "There have been no sessions in the selected period, so there is no new academic progress to summarize."
    return (
        f"During this period, {student_name} attended {sessions_in_period} session(s), "
        f"totaling {hours_in_period} hour(s) of focused support."
    )


def _behavior_phrase(consistency: int) -> str:
    if consistency >= 80:
        return "Engagement appears strong with good follow-through."
    if consistency >= 50:
        return "Engagement is generally good, with room for increased consistency."
    return "Engagement has been spotty and may need additional support."


def _next_steps_phrase(total_outstanding: Decimal, consistency: int) -> str:
    notes = []
    if total_outstanding > 0:
        notes.append("We recommend finalizing outstanding payments to keep the account in good standing.")
    if consistency < 70:
        notes.append("A key next step is to establish a more consistent weekly routine.")
    else:
        notes.append("The next step is to continue the current schedule and monitor ongoing progress.")
    return " ".join(notes)


def get_parent_report_with_narrative(
    db: Session,
    *,
    owner_id: int,
    student_id: int,
    today: date,
    start_date: date | None,
    end_date: date | None,
):
    base_report = get_parent_report(
        db=db,
        owner_id=owner_id,
        student_id=student_id,
        today=today,
        start_date=start_date,
        end_date=end_date,
    )
    # base_report already raises 404 if student missing

    ps = base_report["progress_summary"]
    bs = base_report["billing_summary"]
    student_info = base_report["student"]
    weekly = base_report["weekly_activity_last_8_weeks"]

    student_name = student_info["display_name"]
    total_sessions_all_time = ps["total_sessions_all_time"]
    total_hours_all_time = ps["total_hours_all_time"]
    consistency = ps["consistency_score_0_100"]
    streak = ps["current_session_streak_weeks"]
    sessions_in_period = ps["sessions_in_period"]
    hours_in_period = ps["hours_in_period"]
    total_outstanding = Decimal(bs["total_outstanding_all_time"])
    total_invoiced = bs["total_invoiced_all_time"]
    total_paid = bs["total_paid_all_time"]
    nominal_rate = bs["nominal_rate_per_hour"]
    billing_ratio = bs["billing_vs_usage_ratio"]

    total_sessions_last_8 = sum(w.get("session_count", 0) for w in weekly)

    if total_sessions_all_time == 0:
        overview = f"{student_name} has not started any sessions yet."
    else:
        overview = (
            f"{student_name} has completed {total_sessions_all_time} session(s) "
            f"for a total of {total_hours_all_time} hour(s) of instruction so far."
        )

    attendance = _attendance_phrase(consistency, streak)
    academic_progress = _academic_progress_phrase(student_name, sessions_in_period, hours_in_period)
    behavior = _behavior_phrase(consistency)
    next_steps = _next_steps_phrase(total_outstanding, consistency)
    billing_overview = (
        f"Total billed to date is {total_invoiced}, with {total_paid} paid and "
        f"{bs['total_outstanding_all_time']} remaining. "
        f"The current effective rate is approximately {nominal_rate} per hour of instruction "
        f"(billing vs usage ratio: {billing_ratio})."
    )

    narrative = {
        "overview": overview,
        "attendance": attendance,
        "academic_progress": academic_progress,
        "behavior_and_engagement": behavior,
        "next_steps": next_steps,
        "billing_overview": billing_overview,
    }

    report_with_narrative = dict(base_report)
    report_with_narrative["narrative"] = narrative
    return report_with_narrative
