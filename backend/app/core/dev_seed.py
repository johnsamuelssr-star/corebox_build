import os

from sqlalchemy.orm import Session

from backend.app.core.security import get_password_hash
from backend.app.models.user import User


DEFAULT_DEV_PASSWORD = "Secret123!"
DEFAULT_DEV_USERS = [
    "owner@test.com",
    "owner1@test.com",
]


def ensure_default_dev_owner(db: Session) -> None:
    """
    Create a default owner user for local development if it does not exist.
    Skips execution when running under pytest to avoid altering test expectations.
    """
    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    created = False
    for email in DEFAULT_DEV_USERS:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            continue

        user = User(
            email=email,
            hashed_password=get_password_hash(DEFAULT_DEV_PASSWORD),
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        created = True

    if created:
        db.commit()
