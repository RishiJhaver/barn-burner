import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_token_payload, require_admin
from app.core.config import get_settings
from app.core.security import create_demo_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import (
    AuthConfigResponse,
    AuthResponse,
    ConfirmForgotPasswordRequest,
    ConfirmSignUpRequest,
    DemoTokenRequest,
    DemoTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendCodeRequest,
    SignUpResponse,
    UserResponse,
    UserSyncRequest,
)
from app.services.cognito_service import cognito_service

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


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

    try:
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
    except HTTPException:
        raise
    except Exception as db_err:
        logger.warning("PostgreSQL unavailable during sync_user, returning ephemeral record: %s", db_err)
        user_role = UserRole.ADMIN if str(token_role).lower() == "admin" else UserRole.USER
        now = datetime.now(timezone.utc)
        return User(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, sub),
            cognito_sub=sub,
            email=email,
            username=username,
            role=user_role,
            created_at=now,
            updated_at=now,
        )


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


# ==========================================
# AWS COGNITO DIRECT AUTHENTICATION GATEWAY
# ==========================================

@router.get(
    "/config",
    response_model=AuthConfigResponse,
    summary="Get Authentication Gateway Configuration",
)
async def get_auth_config() -> AuthConfigResponse:
    """Returns public authentication mode details for the frontend."""
    return AuthConfigResponse(
        mock_cognito=settings.MOCK_COGNITO,
        aws_region=settings.AWS_REGION,
        user_pool_id=settings.COGNITO_USER_POOL_ID or "local-mock-pool",
    )


@router.post(
    "/register",
    response_model=SignUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Signs up a new user via AWS Cognito (or local simulator), initiating email verification.",
)
async def register_user(request: RegisterRequest) -> SignUpResponse:
    res = cognito_service.sign_up(
        username=request.username,
        email=str(request.email),
        password=request.password,
        role=request.role.value,
    )
    return SignUpResponse(**res)


@router.post(
    "/confirm-signup",
    summary="Confirm Registration Email OTP Code",
    description="Verifies the email confirmation code to activate the user's account.",
)
async def confirm_sign_up(request: ConfirmSignUpRequest) -> Dict[str, Any]:
    cognito_service.confirm_sign_up(
        username=request.username,
        confirmation_code=request.confirmation_code,
    )
    return {
        "status": "confirmed",
        "message": "Account successfully verified! You can now sign in.",
    }


@router.post(
    "/resend-code",
    summary="Resend Confirmation Code",
    description="Resends the email confirmation code for an unverified account.",
)
async def resend_code(request: ResendCodeRequest) -> Dict[str, Any]:
    res = cognito_service.resend_confirmation_code(request.username)
    return {
        "status": "sent",
        "message": "Verification code has been resent.",
        **res,
    }


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User Login via AWS Cognito",
    description="Authenticates credentials against AWS Cognito or Mock Mode, syncs user into PostgreSQL, and returns JWT tokens.",
)
async def login_user(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    auth_result = cognito_service.initiate_auth(
        username_or_email=request.username_or_email,
        password=request.password,
    )

    claims = auth_result.get("claims", {})
    sub = claims.get("sub") or str(uuid.uuid4())
    email = claims.get("email") or f"{request.username_or_email}@codegrid.dev"
    token_username = claims.get("cognito:username") or claims.get("username") or request.username_or_email
    role_str = claims.get("custom:role", "user")
    user_role = UserRole.ADMIN if str(role_str).lower() == "admin" else UserRole.USER

    # Database synchronization with fallback if database is offline
    user = None
    try:
        stmt = select(User).where((User.cognito_sub == sub) | (User.email == email))
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if user:
            if user.username != token_username:
                user.username = token_username
            user.role = user_role
            await db.commit()
            await db.refresh(user)
        else:
            user = User(
                cognito_sub=sub,
                email=email,
                username=token_username,
                role=user_role,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    except Exception as db_err:
        logger.warning(f"Database sync encountered error: {db_err}. Providing ephemeral user profile.")
        now = datetime.now(timezone.utc)
        user = User(
            id=uuid.uuid4(),
            cognito_sub=sub,
            email=email,
            username=token_username,
            role=user_role,
            created_at=now,
            updated_at=now,
        )

    return AuthResponse(
        access_token=auth_result["access_token"],
        token_type=auth_result.get("token_type", "Bearer"),
        expires_in=auth_result.get("expires_in", 3600),
        user=UserResponse.model_validate(user),
        role=user.role,
    )


@router.post(
    "/forgot-password",
    summary="Request Password Reset OTP",
)
async def forgot_password(request: ForgotPasswordRequest) -> Dict[str, Any]:
    res = cognito_service.forgot_password(request.username_or_email)
    return {
        "status": "code_sent",
        "message": "Password reset code sent to your email.",
        **res,
    }


@router.post(
    "/confirm-forgot-password",
    summary="Confirm Password Reset",
)
async def confirm_forgot_password(request: ConfirmForgotPasswordRequest) -> Dict[str, Any]:
    cognito_service.confirm_forgot_password(
        username=request.username,
        confirmation_code=request.confirmation_code,
        new_password=request.new_password,
    )
    return {
        "status": "success",
        "message": "Password successfully reset! You can now log in with your new password.",
    }

