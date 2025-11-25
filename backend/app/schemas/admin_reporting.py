from pydantic import BaseModel, ConfigDict


class ActivityStudentSummary(BaseModel):
    student_id: int
    student_display_name: str
    session_count: int
    hours: str
    total_invoiced: str
    total_paid: str
    total_outstanding: str

    model_config = ConfigDict(from_attributes=True)


class ActivitySummary(BaseModel):
    session_count: int
    total_hours: str
    total_invoiced: str
    total_paid: str
    total_outstanding: str
    students: list[ActivityStudentSummary]

    model_config = ConfigDict(from_attributes=True)


class AgingBucketTotals(BaseModel):
    current: str
    days_1_30: str
    days_31_60: str
    days_61_90: str
    days_90_plus: str

    model_config = ConfigDict(from_attributes=True)


class StudentAgingSummary(BaseModel):
    student_id: int
    student_display_name: str
    buckets: AgingBucketTotals

    model_config = ConfigDict(from_attributes=True)


class AgingSummary(BaseModel):
    as_of: str
    currency: str | None = "USD"
    totals: AgingBucketTotals
    students: list[StudentAgingSummary]

    model_config = ConfigDict(from_attributes=True)


class InvoiceStatusSummary(BaseModel):
    count: int
    total_amount: str
    total_outstanding: str

    model_config = ConfigDict(from_attributes=True)


class DueWindowSummary(BaseModel):
    count: int
    total_outstanding: str

    model_config = ConfigDict(from_attributes=True)


class InvoicePipelineSummary(BaseModel):
    as_of: str
    currency: str | None = "USD"
    summary: dict
    statuses: dict
    due_windows: dict

    model_config = ConfigDict(from_attributes=True)


class PaymentSummary(BaseModel):
    total_paid_all_time: str
    total_paid_last_7_days: str
    total_paid_last_30_days: str
    payment_count_all_time: int
    average_payment_amount_all_time: str

    model_config = ConfigDict(from_attributes=True)


class WeeklyPaymentPoint(BaseModel):
    year: int
    iso_week: int
    start_date: str
    end_date: str
    total_paid: str
    payment_count: int

    model_config = ConfigDict(from_attributes=True)


class MonthlyPaymentPoint(BaseModel):
    year: int
    month: int
    total_paid: str
    payment_count: int

    model_config = ConfigDict(from_attributes=True)


class PaymentMethodSummary(BaseModel):
    method: str
    total_paid: str
    payment_count: int

    model_config = ConfigDict(from_attributes=True)


class PaymentAnalytics(BaseModel):
    as_of: str
    currency: str | None = "USD"
    summary: PaymentSummary
    weekly_trend: list[WeeklyPaymentPoint]
    monthly_trend: list[MonthlyPaymentPoint]
    methods: list[PaymentMethodSummary]

    model_config = ConfigDict(from_attributes=True)


class StudentWeeklyActivityPoint(BaseModel):
    year: int
    iso_week: int
    start_date: str
    end_date: str
    session_count: int
    hours: str

    model_config = ConfigDict(from_attributes=True)


class StudentKpis(BaseModel):
    total_sessions: int
    total_hours: str
    total_invoiced: str
    total_paid: str
    total_outstanding: str
    last_session_date: str | None
    first_session_date: str | None
    sessions_last_8_weeks: int
    hours_last_8_weeks: str
    consistency_score_0_100: int
    current_session_streak_weeks: int
    billing_vs_usage_ratio: str

    model_config = ConfigDict(from_attributes=True)


class StudentAnalyticsEntry(BaseModel):
    student_id: int
    student_display_name: str
    parent_display_name: str | None
    kpis: StudentKpis
    weekly_activity_last_8_weeks: list[StudentWeeklyActivityPoint]

    model_config = ConfigDict(from_attributes=True)


class StudentAnalyticsReport(BaseModel):
    as_of: str
    students: list[StudentAnalyticsEntry]

    model_config = ConfigDict(from_attributes=True)


class ParentReportStudentInfo(BaseModel):
    id: int
    display_name: str
    parent_display_name: str | None
    contact_email: str | None
    contact_phone: str | None

    model_config = ConfigDict(from_attributes=True)


class ParentReportPeriod(BaseModel):
    start_date: str | None = None
    end_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ParentReportProgressSummary(BaseModel):
    total_sessions_all_time: int
    total_hours_all_time: str
    sessions_in_period: int
    hours_in_period: str
    consistency_score_0_100: int
    current_session_streak_weeks: int
    last_session_date: str | None
    first_session_date: str | None

    model_config = ConfigDict(from_attributes=True)


class ParentReportBillingSummary(BaseModel):
    total_invoiced_all_time: str
    total_paid_all_time: str
    total_outstanding_all_time: str
    nominal_rate_per_hour: str
    billing_vs_usage_ratio: str

    model_config = ConfigDict(from_attributes=True)


class ParentReportWeeklyActivityPoint(BaseModel):
    year: int
    iso_week: int
    start_date: str
    end_date: str
    session_count: int
    hours: str

    model_config = ConfigDict(from_attributes=True)


class ParentReportNotesPlaceholders(BaseModel):
    academic_notes: str
    behavior_notes: str
    next_steps: str

    model_config = ConfigDict(from_attributes=True)


class ParentReport(BaseModel):
    as_of: str
    period: ParentReportPeriod
    student: ParentReportStudentInfo
    progress_summary: ParentReportProgressSummary
    billing_summary: ParentReportBillingSummary
    weekly_activity_last_8_weeks: list[ParentReportWeeklyActivityPoint]
    notes_placeholders: ParentReportNotesPlaceholders

    model_config = ConfigDict(from_attributes=True)


class ParentReportNarrative(BaseModel):
    overview: str
    attendance: str
    academic_progress: str
    behavior_and_engagement: str
    next_steps: str
    billing_overview: str

    model_config = ConfigDict(from_attributes=True)


class ParentReportWithNarrative(BaseModel):
    as_of: str
    period: ParentReportPeriod
    student: ParentReportStudentInfo
    progress_summary: ParentReportProgressSummary
    billing_summary: ParentReportBillingSummary
    weekly_activity_last_8_weeks: list[ParentReportWeeklyActivityPoint]
    notes_placeholders: ParentReportNotesPlaceholders
    narrative: ParentReportNarrative

    model_config = ConfigDict(from_attributes=True)


class ParentReportExport(BaseModel):
    """Represents exported parent report content."""

    content: bytes

    model_config = ConfigDict(from_attributes=True)


# Dashboard card schemas


class OwnerDashboardFinancialCard(BaseModel):
    total_invoiced_all_time: str
    total_paid_all_time: str
    total_outstanding_all_time: str
    total_paid_last_30_days: str

    model_config = ConfigDict(from_attributes=True)


class OwnerDashboardActivityCard(BaseModel):
    total_sessions_all_time: int
    total_hours_all_time: str
    sessions_last_30_days: int
    hours_last_30_days: str

    model_config = ConfigDict(from_attributes=True)


class OwnerDashboardArCard(BaseModel):
    current: str
    days_1_30: str
    days_31_60: str
    days_61_90: str
    days_90_plus: str

    model_config = ConfigDict(from_attributes=True)


class OwnerDashboardPipelineCard(BaseModel):
    draft_count: int
    issued_count: int
    partially_paid_count: int
    paid_count: int
    past_due_count: int
    upcoming_7_days_outstanding: str

    model_config = ConfigDict(from_attributes=True)


class OwnerDashboardSummary(BaseModel):
    as_of: str
    financial: OwnerDashboardFinancialCard
    activity: OwnerDashboardActivityCard
    ar: OwnerDashboardArCard
    pipeline: OwnerDashboardPipelineCard

    model_config = ConfigDict(from_attributes=True)


class StudentDashboardRow(BaseModel):
    student_id: int
    student_display_name: str
    parent_display_name: str | None
    total_sessions_all_time: int
    total_hours_all_time: str
    consistency_score_0_100: int
    current_session_streak_weeks: int
    total_invoiced_all_time: str
    total_paid_all_time: str
    total_outstanding_all_time: str

    model_config = ConfigDict(from_attributes=True)


class StudentDashboardList(BaseModel):
    as_of: str
    students: list[StudentDashboardRow]

    model_config = ConfigDict(from_attributes=True)
