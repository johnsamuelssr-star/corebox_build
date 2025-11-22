"""Timeline services for logging lead events."""

from backend.app.models.timeline import TimelineEvent


def log_event(db, lead_id: int, owner_id: int, event_type: str, description: str) -> TimelineEvent:
    event = TimelineEvent(lead_id=lead_id, owner_id=owner_id, event_type=event_type, description=description)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
