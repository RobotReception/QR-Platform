from typing import Any, Dict, Optional
import logging
import time

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwk, jwt, JWTError
from pydantic import BaseModel
from uuid import UUID

from app.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
settings = get_settings()

# Supabase access tokens are always issued with this audience.
JWT_AUDIENCE = "authenticated"


class CurrentUser(BaseModel):
    id: UUID
    email: Optional[str] = None
    role: Optional[str] = None  # supabase role (authenticated, service_role)


# ── JWKS cache (keyed by kid, refreshed on a TTL) ──
_JWKS_TTL_SECONDS = 3600
_jwks_cache: Dict[str, Any] = {}
_jwks_fetched_at: float = 0.0


def get_supabase_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """Fetch and cache Supabase JWKS for verifying ES256/RS256 tokens.

    Cached in-process for _JWKS_TTL_SECONDS and refreshed on demand when a
    token references an unknown kid (key rotation).
    """
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if not force_refresh and _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        response = httpx.get(jwks_url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        _jwks_cache = {key["kid"]: key for key in data.get("keys", [])}
        _jwks_fetched_at = now
        return _jwks_cache
    except Exception as e:
        if _jwks_cache:
            # Serve stale keys rather than hard-failing on a transient outage.
            logger.warning("JWKS refresh failed, serving cached keys: %s", e)
            return _jwks_cache
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch Supabase JWKS: {e}",
        )


def get_jwk_for_token(token: str) -> Any:
    """Resolve the verification key for a token by its alg/kid.

    Not cached by token (that would grow unbounded and never hit); the
    underlying JWKS is cached by kid in get_supabase_jwks().
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg == "HS256":
        return settings.supabase_jwt_secret

    kid = header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing kid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwks = get_supabase_jwks()
    if kid not in jwks:
        # Possible key rotation — force one refresh before giving up.
        jwks = get_supabase_jwks(force_refresh=True)
    if kid not in jwks:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no matching JWK kid found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return jwk.construct(jwks[kid])


def decode_supabase_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT token."""
    try:
        payload = jwt.decode(
            token,
            get_jwk_for_token(token),
            algorithms=["HS256", "ES256", "RS256"],
            audience=JWT_AUDIENCE,
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Extract current user from a verified Supabase JWT (audience enforced)."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_jwk_for_token(credentials.credentials),
            algorithms=["HS256", "ES256", "RS256"],
            audience=JWT_AUDIENCE,
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    return CurrentUser(
        id=UUID(user_id),
        email=payload.get("email"),
        role=payload.get("role"),
    )


def get_tenant_id_from_header(request: Request) -> UUID:
    """Extract tenant_id from X-Tenant-ID header."""
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    try:
        return UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID format",
        )
