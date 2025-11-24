"""Time utilities for timezone-aware UTC datetimes."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for defaults and onupdate hooks."""
    return datetime.now(UTC)
