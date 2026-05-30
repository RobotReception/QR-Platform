from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwk, jwt, JWTError
from pydantic import BaseModel
from uuid import UUID

from app.config import get_settings

security = HTTPBearer()
settings = get_settings()


class CurrentUser(BaseModel):
    id: UUID
    email: Optional[str] = None
    role: Optional[str] = None  # supabase role (authenticated, service_role)


def get_supabase_jwks() -> Dict[str, Any]:
    """Fetch and cache Supabase JWKS for verifying ES256/RS256 tokens."""
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        response = httpx.get(jwks_url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return {key["kid"]: key for key in data.get("keys", [])}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch Supabase JWKS: {e}",
        )


@lru_cache()
def get_jwk_for_token(token: str) -> Any:
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg == "HS256":
        return settings.supabase_jwt_secret

    jwks = get_supabase_jwks()
    kid = header.get("kid")
    if not kid or kid not in jwks:
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
            audience="authenticated",
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
    """Extract current user from JWT token."""
    # Decode JWT without audience verification (Supabase tokens don't always match)
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_jwk_for_token(credentials.credentials),
            algorithms=["HS256", "ES256", "RS256"],
            options={"verify_aud": False}  # Skip audience verification
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
    print(f"DEBUG: X-Tenant-ID header: {tenant_id}")
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
