"""AuthService — password hashing, token management, user CRUD."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select

from skpl_agent.app._security.jwt_auth import JWTService

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service handling user registration, login, and token management.

    Usage:
        >>> auth_svc = AuthService(storage, jwt_service)
        >>> result = await auth_svc.register("alice", "secure-password")
        >>> result = await auth_svc.login("alice", "secure-password")
    """

    def __init__(self, storage, jwt_service: JWTService):
        self._storage = storage
        self._jwt = jwt_service

    # ------------------------------------------------------------------
    # Session helper (wraps storage._session for future compatibility)
    # ------------------------------------------------------------------

    def _session(self):
        """Get a database session from the storage backend.

        Uses the storage's internal session factory. When StorageBase
        gains a public session API, this should be updated to use it.
        """
        return self._storage._session()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(
        self,
        username: str,
        password: str,
        email: str | None = None,
        role: str = "user",
    ) -> dict:
        from skpl_agent.app._auth.models import UserRow

        async with self._session() as sess:
            result = await sess.execute(
                select(UserRow).where(UserRow.username == username)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Username '{username}' already exists")

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            user = UserRow(
                username=username,
                password_hash=password_hash,
                email=email,
                role=role,
            )
            sess.add(user)
            await sess.commit()

            token = self._jwt.create_token(
                sub=user.id,
                role=user.role,
                metadata={"username": user.username},
            )

            logger.info("User registered: %s (id=%s)", username, user.id)

            return {
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                },
            }

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, username: str, password: str) -> dict:
        from skpl_agent.app._auth.models import UserRow

        async with self._storage._session() as sess:
            result = await sess.execute(
                select(UserRow).where(UserRow.username == username)
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError("Invalid username or password")

            if not bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                raise ValueError("Invalid username or password")

            user.last_login_at = datetime.now(timezone.utc)
            await sess.commit()

            token = self._jwt.create_token(
                sub=user.id,
                role=user.role,
                metadata={"username": user.username},
            )

            logger.info("User logged in: %s", username)

            return {
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                },
            }

    # ------------------------------------------------------------------
    # User lookup
    # ------------------------------------------------------------------

    async def get_user(self, user_id: str) -> dict | None:
        from skpl_agent.app._auth.models import UserRow

        async with self._storage._session() as sess:
            user = await sess.get(UserRow, user_id)
            if user is None:
                return None

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            }
    async def get_user_by_username(self, username: str) -> dict | None:
        from skpl_agent.app._auth.models import UserRow

        async with self._storage._session() as sess:
            result = await sess.execute(
                select(UserRow).where(UserRow.username == username)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            }
