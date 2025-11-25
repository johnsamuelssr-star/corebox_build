"""Export parent report as text-based PDF-like payload."""

from datetime import date, datetime, timezone
from typing import Optional

from backend.app.services.parent_report_narrative_service import get_parent_report_with_narrative


def build_parent_report_export_text(report: dict) -> str:
    period = report.get("period", {})
    student = report.get("student", {})
    ps = report.get("progress_summary", {})
    bs = report.get("billing_summary", {})
    weekly = report.get("weekly_activity_last_8_weeks", [])
    narrative = report.get("narrative", {})

    period_str = "All-time"
    if period.get("start_date") or period.get("end_date"):
        start = period.get("start_date") or ""
        end = period.get("end_date") or ""
        period_str = f"{start} to {end}".strip()

    lines = []
    lines.append("Mindfull Learning - Parent Report")
    lines.append(f"Student: {student.get('display_name', '')}")
    lines.append(f"Parent/Guardian: {student.get('parent_display_name') or 'N/A'}")
    lines.append(f"Period: {period_str}")
    lines.append(f"As of: {report.get('as_of', '')}")
    lines.append("")
    lines.append("== Progress Summary ==")
    lines.append(f"Total sessions (all time): {ps.get('total_sessions_all_time', 0)}")
    lines.append(f"Total hours (all time): {ps.get('total_hours_all_time', '0.00')}")
    lines.append(f"Sessions this period: {ps.get('sessions_in_period', 0)}")
    lines.append(f"Hours this period: {ps.get('hours_in_period', '0.00')}")
    lines.append(f"Consistency score: {ps.get('consistency_score_0_100', 0)} / 100")
    lines.append(f"Current weekly streak: {ps.get('current_session_streak_weeks', 0)} week(s)")
    lines.append(f"First session date: {ps.get('first_session_date') or 'N/A'}")
    lines.append(f"Most recent session: {ps.get('last_session_date') or 'N/A'}")
    lines.append("")
    lines.append("== Billing Summary ==")
    lines.append(f"Total invoiced (all time): {bs.get('total_invoiced_all_time', '0.00')}")
    lines.append(f"Total paid (all time): {bs.get('total_paid_all_time', '0.00')}")
    lines.append(f"Outstanding balance: {bs.get('total_outstanding_all_time', '0.00')}")
    lines.append(f"Nominal rate per hour: {bs.get('nominal_rate_per_hour', '0.00')}")
    lines.append(f"Billing vs usage ratio: {bs.get('billing_vs_usage_ratio', '0.00')}")
    lines.append("")
    lines.append("== Weekly Activity (Last 8 Weeks) ==")
    for entry in weekly:
        lines.append(
            f"Week {entry.get('year')}-W{entry.get('iso_week')}: {entry.get('session_count', 0)} session(s), {entry.get('hours', '0.00')} hour(s)"
        )
    lines.append("")
    lines.append("== Narrative Overview ==")
    lines.append(narrative.get("overview", ""))
    lines.append("")
    lines.append("== Attendance ==")
    lines.append(narrative.get("attendance", ""))
    lines.append("")
    lines.append("== Academic Progress ==")
    lines.append(narrative.get("academic_progress", ""))
    lines.append("")
    lines.append("== Behavior & Engagement ==")
    lines.append(narrative.get("behavior_and_engagement", ""))
    lines.append("")
    lines.append("== Next Steps ==")
    lines.append(narrative.get("next_steps", ""))
    lines.append("")
    lines.append("== Billing Overview ==")
    lines.append(narrative.get("billing_overview", ""))
    lines.append("")

    return "\n".join(lines)


def get_parent_report_export_bytes(
    db,
    *,
    owner_id: int,
    student_id: int,
    today: date,
    start_date: Optional[date],
    end_date: Optional[date],
) -> bytes:
    report = get_parent_report_with_narrative(
        db=db,
        owner_id=owner_id,
        student_id=student_id,
        today=today,
        start_date=start_date,
        end_date=end_date,
    )
    text = build_parent_report_export_text(report)
    return text.encode("utf-8")
