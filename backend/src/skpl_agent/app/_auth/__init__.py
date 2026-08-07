"""SKPL Authentication System — User registration, login, token management.

Provides:
- User model (SQLAlchemy)
- AuthService (password hashing, token management)
- Auth routes (register, login, refresh, me)
"""

from skpl_agent.app._auth.models import UserRow
from skpl_agent.app._auth.service import AuthService
from skpl_agent.app._auth.router import router as auth_router

__all__ = [
    "UserRow",
    "AuthService",
    "auth_router",
]