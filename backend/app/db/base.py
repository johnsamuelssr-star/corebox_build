from sqlalchemy.orm import declarative_base

# Base class for all ORM models
Base = declarative_base()

# Import models to register metadata for Base.metadata.create_all in tests
from backend.app.models.user import User  # noqa: F401
from backend.app.models.lead import Lead  # noqa: F401
from backend.app.models.note import Note  # noqa: F401
from backend.app.models.timeline import TimelineEvent  # noqa: F401
from backend.app.models.reminder import Reminder  # noqa: F401
from backend.app.models.student import Student  # noqa: F401
from backend.app.models.session import Session  # noqa: F401
from backend.app.models.rate_history import RateHistory  # noqa: F401
from backend.app.models.user_preferences import UserPreferences  # noqa: F401
from backend.app.models.invoice_item import InvoiceItem  # noqa: F401
from backend.app.models.invoice_template import InvoiceTemplate  # noqa: F401
from backend.app.models.invoice import Invoice  # noqa: F401
from backend.app.models.payment import Payment  # noqa: F401
from backend.app.models.parent_link import ParentStudentLink  # noqa: F401
