from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    cognito_sub: str = Field(..., max_length=64)
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=2, max_length=100)
    role: UserRole | None = None


class UserSyncRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)


class UserResponse(UserBase):
    id: UUID
    cognito_sub: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DemoTokenRequest(BaseModel):
    role: UserRole = UserRole.USER
    username: str = "coder_dev"
    email: EmailStr = "coder@example.com"
    sub: str | None = None


class DemoTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    claims: dict


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER


class ConfirmSignUpRequest(BaseModel):
    username: str = Field(..., min_length=1)
    confirmation_code: str = Field(..., min_length=1)


class ResendCodeRequest(BaseModel):
    username: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1)


class ConfirmForgotPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1)
    confirmation_code: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class SignUpResponse(BaseModel):
    user_sub: str | None = None
    user_confirmed: bool = False
    delivery_medium: str = "EMAIL"
    destination: str | None = None
    demo_hint: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user: UserResponse
    role: UserRole


class AuthConfigResponse(BaseModel):
    mock_cognito: bool
    aws_region: str
    user_pool_id: str


