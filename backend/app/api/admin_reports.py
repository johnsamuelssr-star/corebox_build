"""Admin/owner financial reporting endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.admin_reporting import ActivitySummary, AgingSummary
from backend.app.services.activity_reporting import get_activity_summary
from backend.app.services.aging_reporting import get_aging_summary
from backend.app.schemas.admin_reporting import (
    InvoicePipelineSummary,
    PaymentAnalytics,
    StudentAnalyticsReport,
    ParentReport,
    ParentReportWithNarrative,
)
from backend.app.services.invoice_pipeline_reporting import get_invoice_pipeline_summary
from backend.app.services.payment_analytics_reporting import get_payment_analytics
from backend.app.services.student_analytics_reporting import get_student_analytics
from backend.app.services.parent_report_service import get_parent_report
from backend.app.services.parent_report_narrative_service import get_parent_report_with_narrative
from backend.app.services.parent_report_export_service import get_parent_report_export_bytes
from backend.app.services.reports import get_financial_summary_for_owner

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


@router.get("/financial-summary")
async def financial_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = get_financial_summary_for_owner(db, current_user.id, start_date, end_date)
    return summary


@router.get("/activity-summary", response_model=ActivitySummary)
async def activity_summary(
    start_date: date | None = None,
    end_date: date | None = None,  # accepted for compatibility but not used
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_activity_summary(db, owner_id=current_user.id, start_date=start_date)


@router.get("/aging-summary", response_model=AgingSummary)
async def aging_summary(
    as_of: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_aging_summary(db, owner_id=current_user.id, as_of=as_of)


@router.get("/invoice-pipeline", response_model=InvoicePipelineSummary)
async def invoice_pipeline(
    today: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_invoice_pipeline_summary(db, owner_id=current_user.id, today=today)


@router.get("/payment-analytics", response_model=PaymentAnalytics)
async def payment_analytics(
    today: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_payment_analytics(db, owner_id=current_user.id, today=today)


@router.get("/student-analytics", response_model=StudentAnalyticsReport)
async def student_analytics(
    today: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_student_analytics(db, owner_id=current_user.id, today=today)


@router.get("/parent-report/{student_id}", response_model=ParentReport)
async def parent_report(
    student_id: int,
    today: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_today = today or date.today()
    return get_parent_report(
        db=db,
        owner_id=current_user.id,
        student_id=student_id,
        today=effective_today,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/parent-report/{student_id}/narrative", response_model=ParentReportWithNarrative)
async def parent_report_narrative(
    student_id: int,
    today: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_today = today or date.today()
    return get_parent_report_with_narrative(
        db=db,
        owner_id=current_user.id,
        student_id=student_id,
        today=effective_today,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/parent-report/{student_id}/export/pdf",
    response_class=Response,
)
async def parent_report_export_pdf(
    student_id: int,
    today: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_today = today or date.today()
    pdf_bytes = get_parent_report_export_bytes(
        db=db,
        owner_id=current_user.id,
        student_id=student_id,
        today=effective_today,
        start_date=start_date,
        end_date=end_date,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="parent_report_{student_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
