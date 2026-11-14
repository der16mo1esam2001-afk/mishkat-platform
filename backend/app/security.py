from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Callable
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .settings import settings

bearer = HTTPBearer(auto_error=False)

ALLOWED_ROLES = {"authenticated", "platform_admin", "domain_operator", "auditor", "learner"}


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str | None
    role: str
    claims: dict[str, Any]

    def has_role(self, *roles: str) -> bool:
        if "platform_admin" in (self.role, *self.claims.get("roles", [])):
            return True
        user_roles = {self.role, *self.claims.get("roles", [])}
        return bool(user_roles.intersection(roles))


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_jwks_url:
        raise RuntimeError("SUPABASE_JWKS_URL is not configured")
    return PyJWKClient(settings.supabase_jwks_url, cache_keys=True, lifespan=300)


def _decode_token(token: str) -> dict[str, Any]:
    if settings.auth_mode == "development":
        if not settings.dev_auth_enabled:
            raise HTTPException(status_code=503, detail="Development authentication is disabled")
        try:
            return jwt.decode(
                token,
                settings.dev_auth_secret,
                algorithms=["HS256"],
                audience=settings.jwt_audience,
                issuer="mishkat-local-development",
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired development token") from exc

    if settings.auth_mode == "supabase_jwks":
        if not settings.supabase_issuer or not settings.supabase_jwks_url:
            raise HTTPException(status_code=503, detail="Supabase JWT verification is not configured")
        try:
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience=settings.jwt_audience,
                issuer=settings.supabase_issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except (jwt.PyJWTError, RuntimeError) as exc:
            raise HTTPException(status_code=401, detail="Invalid authentication token") from exc

    raise HTTPException(status_code=503, detail="Unsupported authentication mode")


def get_current_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    claims = _decode_token(credentials.credentials)
    role = claims.get("role", "authenticated")
    if role not in ALLOWED_ROLES and not any(r in ALLOWED_ROLES for r in claims.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An authenticated user token is required")
    try:
        user_id = UUID(str(claims["sub"]))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Token subject is invalid") from exc
    return Principal(
        user_id=user_id,
        email=claims.get("email"),
        role=str(role),
        claims=claims,
    )


def require_role(*required_roles: str) -> Callable[[Principal], Principal]:
    """Dependency enforcing RBAC scopes on route handlers."""
    def role_checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_role(*required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(required_roles)}",
            )
        return principal
    return role_checker


def issue_local_development_token(
    user_id: UUID | None = None,
    role: str = "authenticated",
    email: str = "local-user@mishkat.invalid",
    expires_in_hours: int = 2,
) -> dict[str, Any]:
    if settings.environment != "development" or settings.auth_mode != "development" or not settings.dev_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    now = datetime.now(timezone.utc)
    uid = user_id or UUID("9e3c8e5e-ef0b-4ca7-8ae5-7c15f6a9e201")
    payload = {
        "sub": str(uid),
        "email": email,
        "role": role,
        "iss": "mishkat-local-development",
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(hours=expires_in_hours),
    }
    token = jwt.encode(payload, settings.dev_auth_secret, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in_hours * 3600,
        "role": role,
        "user_id": str(uid),
        "mode": "LOCAL DEVELOPMENT ONLY",
    }
