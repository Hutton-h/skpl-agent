"""JWT authentication — token-based auth for WebSocket and API endpoints.

Provides JWT creation, validation, and middleware integration for
securing desktop node WebSocket connections and API endpoints.

Supports:
- HS256 symmetric signing
- Token expiration and refresh
- Role-based claims (desktop-node, admin, agent)
- Integration with FastAPI dependency injection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class JWTClaims:
    """Decoded JWT claims."""

    sub: str  # Subject (node_id, agent_id, or user_id)
    role: str = "agent"  # desktop-node, admin, agent
    exp: float = 0.0
    iat: float = 0.0
    jti: str = ""  # Unique token ID
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        if self.exp == 0:
            return False
        return datetime.now(timezone.utc).timestamp() > self.exp

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JWTClaims:
        """Create from a decoded JWT dictionary."""
        return cls(
            sub=data.get("sub", ""),
            role=data.get("role", "agent"),
            exp=data.get("exp", 0),
            iat=data.get("iat", 0),
            jti=data.get("jti", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Auth Error
# ---------------------------------------------------------------------------


class JWTAuthError(Exception):
    """Base exception for JWT authentication errors."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TokenExpiredError(JWTAuthError):
    """Token has expired."""

    def __init__(self):
        super().__init__("Token has expired", 401)


class InvalidTokenError(JWTAuthError):
    """Token is invalid or malformed."""

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail, 401)


class InsufficientRoleError(JWTAuthError):
    """Token does not have the required role."""

    def __init__(self, required: str, actual: str):
        super().__init__(
            f"Insufficient role: required '{required}', got '{actual}'",
            403,
        )


# ---------------------------------------------------------------------------
# JWT Service
# ---------------------------------------------------------------------------


class JWTService:
    """JWT token creation and validation service.

    Usage:
        >>> svc = JWTService(secret="my-secret-key")
        >>> token = svc.create_token(sub="node-1", role="desktop-node")
        >>> claims = svc.verify_token(token)
        >>> print(claims.role)
        desktop-node
    """

    DEFAULT_ALGORITHM = "HS256"
    DEFAULT_EXPIRY_HOURS = 24

    def __init__(
        self,
        secret: str,
        algorithm: str = DEFAULT_ALGORITHM,
        default_expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> None:
        if not secret or secret == "change-me-in-production":
            logger.warning(
                "JWT secret is not set or using default value. "
                "Set SKPL_JWT_SECRET in production."
            )

        self._secret = secret
        self._algorithm = algorithm
        self._default_expiry = timedelta(hours=default_expiry_hours)

    def create_token(
        self,
        sub: str,
        role: str = "agent",
        expiry: timedelta | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a signed JWT token.

        Args:
            sub: Subject identifier (node_id, agent_id, etc.).
            role: Role for authorization (desktop-node, admin, agent).
            expiry: Custom expiry duration. Defaults to 24 hours.
            metadata: Additional claims to include in the token.

        Returns:
            Signed JWT token string.
        """
        import uuid

        now = datetime.now(timezone.utc)
        exp = now + (expiry or self._default_expiry)

        payload: dict[str, Any] = {
            "sub": sub,
            "role": role,
            "iat": now.timestamp(),
            "exp": exp.timestamp(),
            "jti": str(uuid.uuid4()),
            "metadata": metadata or {},
        }

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token

    def verify_token(self, token: str) -> JWTClaims:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token string to verify.

        Returns:
            Decoded JWTClaims.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": True},
            )
            claims = JWTClaims.from_dict(payload)

            if claims.is_expired:
                raise TokenExpiredError()

            return claims

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(str(e))
        except Exception as e:
            raise InvalidTokenError(f"Token verification failed: {e}")

    def verify_role(self, token: str, required_role: str) -> JWTClaims:
        """Verify a token and check that it has the required role.

        Args:
            token: The JWT token string.
            required_role: The minimum role required.

        Returns:
            Decoded JWTClaims if the role check passes.

        Raises:
            InsufficientRoleError: If the token's role is insufficient.
        """
        claims = self.verify_token(token)

        # Role hierarchy: admin > agent > user > desktop-node
        role_hierarchy = {"admin": 4, "agent": 3, "user": 2, "desktop-node": 1}

        if role_hierarchy.get(claims.role, 0) < role_hierarchy.get(required_role, 0):
            raise InsufficientRoleError(required_role, claims.role)

        return claims

    def refresh_token(self, token: str, expiry: timedelta | None = None) -> str:
        """Create a new token with the same claims but updated expiry.

        Args:
            token: The existing (possibly expired) token.
            expiry: New expiry duration.

        Returns:
            A new JWT token string.

        Raises:
            InvalidTokenError: If the token is malformed (expired is OK).
        """
        try:
            # Decode without expiry verification to allow refreshing expired tokens
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Cannot refresh invalid token: {e}")

        return self.create_token(
            sub=payload.get("sub", ""),
            role=payload.get("role", "agent"),
            expiry=expiry,
            metadata=payload.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# FastAPI Integration
# ---------------------------------------------------------------------------


class JWTBearer(HTTPBearer):
    """FastAPI dependency for JWT authentication.

    Usage:
        >>> jwt_bearer = JWTBearer(jwt_service)
        >>> @app.get("/protected")
        >>> async def protected(claims: JWTClaims = Depends(jwt_bearer)):
        ...     return {"user": claims.sub}
    """

    def __init__(
        self,
        jwt_service: JWTService,
        auto_error: bool = True,
    ) -> None:
        super().__init__(auto_error=auto_error)
        self._jwt_service = jwt_service

    async def __call__(self, request: Request) -> JWTClaims:
        """Extract and verify JWT from the request."""
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(request)

        if credentials is None:
            if self.auto_error:
                raise HTTPException(status_code=401, detail="Not authenticated")
            raise InvalidTokenError("No credentials provided")

        token = credentials.credentials
        try:
            return self._jwt_service.verify_token(token)
        except TokenExpiredError:
            raise HTTPException(status_code=401, detail="Token expired")
        except InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=str(e))


def require_role(required_role: str):
    """FastAPI dependency factory: require a minimum role.

    Usage:
        >>> @app.get("/admin")
        >>> async def admin_only(
        ...     claims: JWTClaims = Depends(require_role("admin"))
        ... ):
        ...     return {"admin": True}
    """

    async def _dependency(
        request: Request,
        jwt_service: JWTService = Depends(),
    ) -> JWTClaims:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = auth_header[7:]
        try:
            return jwt_service.verify_role(token, required_role)
        except TokenExpiredError:
            raise HTTPException(status_code=401, detail="Token expired")
        except InsufficientRoleError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=str(e))

    return _dependency


def extract_token_from_ws(websocket_headers: dict[str, str]) -> str | None:
    """Extract JWT token from WebSocket connection headers.

    Checks in order:
    1. Authorization header (Bearer token)
    2. Sec-WebSocket-Protocol header (token sub-protocol)
    3. Query parameter 'token'

    Returns the token string or None.
    """
    # Method 1: Authorization header
    auth = websocket_headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]

    # Method 2: WebSocket sub-protocol
    protocols = websocket_headers.get("sec-websocket-protocol", "")
    if protocols:
        return protocols

    return None