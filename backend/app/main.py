# Codex local edit test
# Initial CoreBox CRM backend entrypoint ??" minimal FastAPI app.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.settings import get_settings
from backend.app.api import auth
from backend.app.api import register
from backend.app.api import login
from backend.app.api import protected
from backend.app.api import leads
from backend.app.api import notes
from backend.app.api import timeline
from backend.app.api import reminders
from backend.app.api import students
from backend.app.api import sessions
from backend.app.api import dashboard
from backend.app.api import admin_dashboard
from backend.app.api import rates
from backend.app.api import preferences
from backend.app.api import profile
from backend.app.api import admin_users
from backend.app.api import invoice_templates
from backend.app.api import invoices
from backend.app.api import admin_invoices
from backend.app.api import payments
from backend.app.api import reports
from backend.app.api import revenue
from backend.app.api import admin_reports
from backend.app.api import enrollments
from backend.app.api import parent
from backend.app.api import admin_parents
from backend.app.api import parent_portal
from backend.app.api import owner
from backend.app.core.dev_seed import ensure_default_dev_owner
from backend.app.db.session import SessionLocal

app = FastAPI()
settings = get_settings()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(protected.router)
app.include_router(leads.router)
app.include_router(notes.router)
app.include_router(timeline.router)
app.include_router(reminders.router)
app.include_router(students.router)
app.include_router(sessions.router)
app.include_router(dashboard.router)
app.include_router(admin_dashboard.router)
app.include_router(rates.router)
app.include_router(preferences.router)
app.include_router(profile.router)
app.include_router(admin_users.router)
app.include_router(invoice_templates.router)
app.include_router(invoices.router)
app.include_router(admin_invoices.router)
app.include_router(payments.router)
app.include_router(reports.router)
app.include_router(revenue.router)
app.include_router(admin_reports.router)
app.include_router(enrollments.router)
app.include_router(parent.router)
app.include_router(admin_parents.router)
app.include_router(parent_portal.router)
app.include_router(owner.router)


@app.get("/")
def read_root():
    return {"app": "CoreBox CRM backend", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
def seed_default_dev_owner():
    db = SessionLocal()
    try:
        ensure_default_dev_owner(db)
    finally:
        db.close()
