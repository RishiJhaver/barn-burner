"""Security, JWT cryptographic validation, and Cognito JWKS verification."""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import httpx
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

# In-memory cache for Cognito JWKS: {"keys": [...], "expires_at": float}
_jwks_cache: Dict[str, Any] = {}
JWKS_CACHE_TTL_SECONDS = 3600  # Cache keys for 1 hour


async def get_cognito_jwks() -> Dict[str, Any]:
    """Fetch and cache public JSON Web Key Set (JWKS) from AWS Cognito."""
    current_time = time.time()
    if _jwks_cache and _jwks_cache.get("expires_at", 0) > current_time:
        return _jwks_cache["data"]

    jwks_url = settings.jwks_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            data = response.json()
            _jwks_cache["data"] = data
            _jwks_cache["expires_at"] = current_time + JWKS_CACHE_TTL_SECONDS
            return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch Cognito public keys: {str(e)}",
        )


def create_demo_access_token(
    sub: str,
    email: str,
    username: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a mock Cognito-compatible JWT token for local testing."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=7)

    payload = {
        "sub": sub,
        "email": email,
        "cognito:username": username,
        "username": username,
        "custom:role": role,
        "token_use": "access",
        "iss": "mock-cognito-issuer",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.DEMO_JWT_SECRET, algorithm="HS256")


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode incoming JWT token.
    Supports Dual-Mode:
    - Mock/Demo Mode (HS256 via DEMO_JWT_SECRET) when MOCK_COGNITO is True.
    - AWS Cognito RS256 JWKS verification when MOCK_COGNITO is False.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if settings.MOCK_COGNITO:
        try:
            payload = jwt.decode(
                token,
                settings.DEMO_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            return payload
        except JWTError:
            raise credentials_exception

    # Production AWS Cognito RS256 verification
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise credentials_exception

        jwks = await get_cognito_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found in JWKS",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.COGNITO_ISSUER if settings.COGNITO_ISSUER else None,
            options={
                "verify_exp": True,
                "verify_iss": bool(settings.COGNITO_ISSUER),
            },
        )
        return payload
    except JWTError:
        raise credentials_exception
