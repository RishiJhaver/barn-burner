"""FastAPI dependencies for database sessions, JWT verification, and RBAC."""

from typing import Any, AsyncGenerator, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import verify_jwt_token
from app.models.enums import UserRole
from app.models.user import User

# HTTPBearer security scheme (shows Authorize button with Bearer token in Swagger UI)
security_scheme = HTTPBearer(auto_error=True)


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    Extract and verify Bearer JWT token.
    Returns decoded token payload containing user claims (sub, email, username, role).
    """
    token = credentials.credentials
    return await verify_jwt_token(token)


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the current authenticated user from PostgreSQL using the Cognito sub claim.
    If the user has not called /auth/sync yet, returns HTTP 404.
    """
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.cognito_sub == sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Just-In-Time (JIT) auto-provisioning: automatically create user from valid JWT claims
        email = payload.get("email") or f"{sub[:8]}@example.com"
        token_username = payload.get("cognito:username") or payload.get("username") or email.split("@")[0]
        token_role = payload.get("custom:role", "user")
        user_role = UserRole.ADMIN if str(token_role).lower() == "admin" else UserRole.USER

        # Ensure username uniqueness
        username = token_username
        check_stmt = select(User).where(User.username == username)
        if (await db.execute(check_stmt)).scalar_one_or_none():
            username = f"{token_username}_{sub[:4]}"

        user = User(
            cognito_sub=sub,
            email=email,
            username=username,
            role=user_role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Role-based access control dependency ensuring the user has the 'admin' role.
    Raises HTTP 403 Forbidden if the user is a standard 'user'.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to perform this action.",
        )
    return current_user
