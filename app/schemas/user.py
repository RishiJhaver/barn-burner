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

