"""Auth routes — register, login, refresh, get current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from skpl_agent.app._security.jwt_auth import JWTClaims, JWTBearer

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Registration request body."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = None


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    token: str
    user: dict


class UserResponse(BaseModel):
    """User info response."""

    id: str
    username: str
    email: str | None
    role: str
    created_at: str | None
    last_login_at: str | None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_auth_service(request: Request):
    """Get the AuthService from app state."""
    svc = getattr(request.app.state, "auth_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503,
            detail="Auth service is not configured",
        )
    return svc


async def _get_jwt_claims(request: Request) -> JWTClaims:
    """Extract JWT claims from the request using the app's JWTBearer."""
    jwt_bearer = getattr(request.app.state, "jwt_bearer", None)
    if jwt_bearer is None:
        raise HTTPException(
            status_code=503,
            detail="JWT authentication is not configured",
        )
    return await jwt_bearer(request)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    auth_svc=Depends(_get_auth_service),
):
    """Register a new user account.

    Returns a JWT token that can be used for authenticated requests.
    """
    try:
        return await auth_svc.register(
            username=body.username,
            password=body.password,
            email=body.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_svc=Depends(_get_auth_service),
):
    """Log in with username and password.

    Returns a JWT token valid for 24 hours.
    """
    try:
        return await auth_svc.login(
            username=body.username,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    claims: JWTClaims = Depends(_get_jwt_claims),
):
    """Refresh an existing JWT token.

    The old token (even if expired) can be used to obtain a new one.
    Requires a valid Authorization header.
    """
    jwt_svc = getattr(request.app.state, "jwt_service", None)
    if jwt_svc is None:
        raise HTTPException(status_code=503, detail="JWT service not configured")

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        new_token = jwt_svc.refresh_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    auth_svc = _get_auth_service(request)
    user = await auth_svc.get_user(claims.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return {"token": new_token, "user": user}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    claims: JWTClaims = Depends(_get_jwt_claims),
):
    """Get the currently authenticated user's profile."""
    auth_svc = _get_auth_service(request)
    user = await auth_svc.get_user(claims.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return UserResponse(**user)