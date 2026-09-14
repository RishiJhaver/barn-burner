"""Authentication endpoints for user sync, profile retrieval, and demo token generation."""

import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_token_payload, require_admin
from app.core.config import get_settings
from app.core.security import create_demo_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import DemoTokenRequest, DemoTokenResponse, UserResponse, UserSyncRequest

router = APIRouter()
settings = get_settings()


@router.post(
    "/demo-token",
    response_model=DemoTokenResponse,
    summary="Generate Demo JWT Token (Local Development)",
    description="Generates a mock Cognito-compatible JWT token for testing user and admin workflows without AWS.",
)
async def generate_demo_token(request: DemoTokenRequest = DemoTokenRequest()) -> DemoTokenResponse:
    if not settings.MOCK_COGNITO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo token generator is disabled when live AWS Cognito is active.",
        )

    user_sub = request.sub or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{request.username}@{request.role.value}"))
    role_str = request.role.value

    token = create_demo_access_token(
        sub=user_sub,
        email=str(request.email),
        username=request.username,
        role=role_str,
    )

    return DemoTokenResponse(
        access_token=token,
        token_type="bearer",
        role=request.role,
        claims={
            "sub": user_sub,
            "email": str(request.email),
            "username": request.username,
            "custom:role": role_str,
        },
    )


@router.post(
    "/sync",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Authenticated User into PostgreSQL",
    description="Idempotently creates or updates the local user profile in PostgreSQL using JWT claims from Cognito or Demo Auth.",
)
async def sync_user(
    sync_req: UserSyncRequest | None = None,
    payload: Dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    sub = payload.get("sub")
    email = payload.get("email")
    token_username = payload.get("cognito:username") or payload.get("username")
    token_role = payload.get("custom:role", "user")

    if not sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JWT token is missing mandatory 'sub' or 'email' claims.",
        )

    username = (sync_req.username if sync_req and sync_req.username else None) or token_username or email.split("@")[0]

    # Check if username is already taken by another user
    username_stmt = select(User).where(User.username == username, User.cognito_sub != sub)
    username_res = await db.execute(username_stmt)
    if username_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already taken by another user.",
        )

    # Idempotent lookup by cognito_sub
    stmt = select(User).where(User.cognito_sub == sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Existing user: update username if changed
        if user.username != username:
            user.username = username
            await db.commit()
            await db.refresh(user)
        return user

    # Determine role
    user_role = UserRole.ADMIN if str(token_role).lower() == "admin" else UserRole.USER

    # Check if email is already taken by a different sub
    email_stmt = select(User).where(User.email == email)
    email_res = await db.execute(email_stmt)
    if email_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists under a different identifier.",
        )

    # Create new user row
    new_user = User(
        cognito_sub=sub,
        email=email,
        username=username,
        role=user_role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Retrieves the current authenticated user record and role from PostgreSQL.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return current_user


@router.get(
    "/admin-check",
    summary="Verify Admin Privileges (RBAC Guard)",
    description="Endpoint protected by require_admin dependency. Returns 200 for admins, 403 for standard users.",
)
async def admin_check(
    admin_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    return {
        "status": "authorized",
        "message": f"Welcome Admin {admin_user.username}!",
        "user_id": str(admin_user.id),
        "role": admin_user.role.value,
    }
