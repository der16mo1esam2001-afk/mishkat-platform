from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .settings import settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str | None
    role: str
    claims: dict[str, Any]


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
    if claims.get("role") != "authenticated":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An authenticated user token is required")
    try:
        user_id = UUID(str(claims["sub"]))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Token subject is invalid") from exc
    return Principal(
        user_id=user_id,
        email=claims.get("email"),
        role=str(claims.get("role", "authenticated")),
        claims=claims,
    )


def issue_local_development_token() -> dict[str, Any]:
    if settings.environment != "development" or settings.auth_mode != "development" or not settings.dev_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    now = datetime.now(timezone.utc)
    user_id = UUID("9e3c8e5e-ef0b-4ca7-8ae5-7c15f6a9e201")
    payload = {
        "sub": str(user_id),
        "email": "local-user@mishkat.invalid",
        "role": "authenticated",
        "iss": "mishkat-local-development",
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(hours=2),
    }
    token = jwt.encode(payload, settings.dev_auth_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_in": 7200, "mode": "LOCAL DEVELOPMENT ONLY"}
