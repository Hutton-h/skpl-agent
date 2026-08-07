"""User model for SKPL authentication system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from skpl_agent.app.storage._sql._tables import _Base


class UserRow(_Base):
    """User account stored in the ``users`` table.

    Fields:
        id: UUID primary key.
        username: Unique username (3-100 chars).
        password_hash: bcrypt hash of the password.
        email: Optional email address.
        role: ``"user"`` or ``"admin"``.
        created_at: Account creation timestamp.
        last_login_at: Last successful login timestamp.
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at = Column(DateTime, nullable=True)