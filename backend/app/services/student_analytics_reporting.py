"""Student analytics reporting for owners."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice
from backend.app.models.payment import Payment
from backend.app.models.session import Session as SessionModel
from backend.app.models.student import Student


def _last_n_iso_weeks(today: date, n: int = 8) -> List[Tuple[int, int]]:
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


def _week_start_end(iso_year: int, iso_week: int) -> Tuple[date, date]:
    first_day = datetime.strptime(f"{iso_year} {iso_week} 1", "%G %V %u").date()
    return first_day, first_day + timedelta(days=6)


def get_student_analytics(db: Session, *, owner_id: int, today: date | None = None) -> dict:
    as_of_date = today or datetime.now(timezone.utc).date()
    students: List[Student] = db.query(Student).filter(Student.owner_id == owner_id).all()
    if not students:
        return {"as_of": as_of_date.isoformat(), "students": []}

    student_ids = [s.id for s in students]
    sessions: List[SessionModel] = db.query(SessionModel).filter(SessionModel.student_id.in_(student_ids)).all()
    invoices: List[Invoice] = (
        db.query(Invoice).filter(Invoice.student_id.in_(student_ids), Invoice.owner_id == owner_id).all()
    )
    payments: List[Payment] = (
        db.query(Payment)
        .filter(Payment.invoice_id.in_([inv.id for inv in invoices]), Payment.owner_id == owner_id)
        .all()
    )

    # Map invoices and payments per student
    invoices_by_student: Dict[int, List[Invoice]] = {sid: [] for sid in student_ids}
    for inv in invoices:
        invoices_by_student.setdefault(inv.student_id, []).append(inv)

    payments_by_invoice: Dict[int, List[Payment]] = {}
    for pay in payments:
        payments_by_invoice.setdefault(pay.invoice_id, []).append(pay)

    # Precompute per-student sessions grouping
    sessions_by_student: Dict[int, List[SessionModel]] = {sid: [] for sid in student_ids}
    for sess in sessions:
        sessions_by_student.setdefault(sess.student_id, []).append(sess)

    week_keys = _last_n_iso_weeks(as_of_date, 8)

    report_students = []

    for student in students:
        stu_sessions = sessions_by_student.get(student.id, [])
        stu_invoices = invoices_by_student.get(student.id, [])

        total_sessions = len(stu_sessions)
        total_minutes = sum((s.duration_minutes or 0) for s in stu_sessions)
        total_hours = Decimal(total_minutes) / Decimal("60") if total_minutes else Decimal("0.00")

        session_dates = [s.session_date.date() for s in stu_sessions] if stu_sessions else []
        last_session_date = max(session_dates).isoformat() if session_dates else None
        first_session_date = min(session_dates).isoformat() if session_dates else None

        # Weekly activity
        weekly_map = {key: {"session_count": 0, "hours": Decimal("0.00")} for key in week_keys}
        for sess in stu_sessions:
            sy, sw, _ = sess.session_date.date().isocalendar()
            key = (sy, sw)
            if key in weekly_map:
                weekly_map[key]["session_count"] += 1
                weekly_map[key]["hours"] += Decimal(sess.duration_minutes or 0) / Decimal("60")

        weekly_activity = []
        for year, week in week_keys:
            start_d, end_d = _week_start_end(year, week)
            weekly_activity.append(
                {
                    "year": year,
                    "iso_week": week,
                    "start_date": start_d.isoformat(),
                    "end_date": end_d.isoformat(),
                    "session_count": weekly_map[(year, week)]["session_count"],
                    "hours": str(weekly_map[(year, week)]["hours"].quantize(Decimal("0.01"))),
                }
            )

        sessions_last_8 = sum(w["session_count"] for w in weekly_activity)
        hours_last_8 = sum(Decimal(w["hours"]) for w in weekly_activity)
        weeks_with_sessions = sum(1 for w in weekly_activity if w["session_count"] > 0)
        consistency_score = round(100 * weeks_with_sessions / 8) if weekly_activity else 0

        # Streak from newest backward
        streak = 0
        for wk in reversed(weekly_activity):
            if wk["session_count"] > 0:
                streak += 1
            else:
                break

        # Billing metrics: paid/outstanding from invoices, invoiced from nominal session rates
        nominal_total = sum((Decimal(str(sess.rate_per_hour or 0)) for sess in stu_sessions), Decimal("0.00"))
        valid_invoices = [inv for inv in stu_invoices if inv.status != "void"]
        invoice_ids = [inv.id for inv in valid_invoices]
        stu_payment_total = Decimal("0.00")
        if invoice_ids:
            payment_sum = (
                db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(Payment.invoice_id.in_(invoice_ids), Payment.owner_id == owner_id)
                .scalar()
            )
            stu_payment_total = Decimal(str(payment_sum or 0))
        # Invoiced total for student analytics: sum of per-session nominal rates (not hours-based)
        total_invoiced = nominal_total
        # Outstanding: nominal minus paid (no negative outstanding)
        total_outstanding = total_invoiced - stu_payment_total
        if total_outstanding < Decimal("0"):
            total_outstanding = Decimal("0.00")

        if total_hours > 0:
            billing_vs_usage_ratio_dec = total_invoiced / Decimal(str(total_hours))
        else:
            billing_vs_usage_ratio_dec = Decimal("0")
        billing_vs_usage_ratio = billing_vs_usage_ratio_dec.quantize(Decimal("0.01"))

        report_students.append(
            {
                "student_id": student.id,
                "student_display_name": student.student_name,
                "parent_display_name": student.parent_name if hasattr(student, "parent_name") else None,
                "kpis": {
                    "total_sessions": total_sessions,
                    "total_hours": str(total_hours.quantize(Decimal("0.01"))),
                    "total_invoiced": str(total_invoiced.quantize(Decimal("0.01"))),
                    "total_paid": str(stu_payment_total.quantize(Decimal("0.01"))),
                    "total_outstanding": str(total_outstanding.quantize(Decimal("0.01"))),
                    "last_session_date": last_session_date,
                    "first_session_date": first_session_date,
                    "sessions_last_8_weeks": sessions_last_8,
                    "hours_last_8_weeks": str(hours_last_8.quantize(Decimal("0.01"))),
                    "consistency_score_0_100": consistency_score,
                    "current_session_streak_weeks": streak,
                    "billing_vs_usage_ratio": str(billing_vs_usage_ratio),
                },
                "weekly_activity_last_8_weeks": weekly_activity,
            }
        )

    return {"as_of": as_of_date.isoformat(), "students": report_students}
