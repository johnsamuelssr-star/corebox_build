# Codex local edit test
# Initial CoreBox CRM backend entrypoint ??" minimal FastAPI app.

from fastapi import FastAPI
from backend.app.core.settings import get_settings
from backend.app.api import auth
from backend.app.api import register
from backend.app.api import login
from backend.app.api import protected
from backend.app.api import leads
from backend.app.api import notes
from backend.app.api import timeline
from backend.app.api import reminders

app = FastAPI()
settings = get_settings()
app.include_router(auth.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(protected.router)
app.include_router(leads.router)
app.include_router(notes.router)
app.include_router(timeline.router)
app.include_router(reminders.router)


@app.get("/")
def read_root():
    return {"app": "CoreBox CRM backend", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
