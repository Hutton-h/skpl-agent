"""Security package."""
from skpl_agent.app._security.ssrf import SSRFProtection, SSRFError
from skpl_agent.app._security.jwt_auth import (
    JWTService,
    JWTBearer,
    JWTClaims,
    JWTAuthError,
    TokenExpiredError,
    InvalidTokenError,
    InsufficientRoleError,
    require_role,
    extract_token_from_ws,
)

__all__ = [
    "SSRFProtection",
    "SSRFError",
    "JWTService",
    "JWTBearer",
    "JWTClaims",
    "JWTAuthError",
    "TokenExpiredError",
    "InvalidTokenError",
    "InsufficientRoleError",
    "require_role",
    "extract_token_from_ws",
]