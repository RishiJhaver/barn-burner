"""AWS Cognito Authentication & User Management Service.

Provides a unified interface for User Pool authentication:
- Sign Up (Registration)
- Confirm Sign Up (Email OTP Verification)
- Resend Confirmation Code
- Initiate Auth (Login with USER_PASSWORD_AUTH)
- Forgot Password & Confirm Forgot Password
- Dual-mode support: Live AWS Cognito via Boto3 + Local Mock Simulator for dev/testing.
"""

import logging
import uuid
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import create_demo_access_token

logger = logging.getLogger(__name__)
settings = get_settings()


class CognitoService:
    """Service wrapper for AWS Cognito Identity Provider operations."""

    def __init__(self):
        self.client = None
        if not settings.MOCK_COGNITO:
            try:
                self.client = boto3.client(
                    "cognito-idp",
                    region_name=settings.AWS_REGION,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize live Cognito client: {e}. Falling back to mock mode.")

        # Local in-memory mock store for developer/testing mode
        self._mock_users: Dict[str, Dict[str, Any]] = {
            "alex_coder": {
                "sub": "alex-coder-sub-1111",
                "username": "alex_coder",
                "email": "alex@codegrid.dev",
                "password": "Password123!",
                "role": "user",
                "confirmed": True,
                "confirmation_code": "123456",
            },
            "elena_admin": {
                "sub": "elena-admin-sub-2222",
                "username": "elena_admin",
                "email": "elena@codegrid.dev",
                "password": "Password123!",
                "role": "admin",
                "confirmed": True,
                "confirmation_code": "123456",
            },
            "neo_coder": {
                "sub": "neo-coder-sub-3333",
                "username": "neo_coder",
                "email": "neo@cybercode.matrix",
                "password": "Password123!",
                "role": "user",
                "confirmed": True,
                "confirmation_code": "123456",
            },
        }

    # ==========================================
    # 1. SIGN UP (REGISTRATION)
    # ==========================================
    def sign_up(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "user",
    ) -> Dict[str, Any]:
        """Register a new user in AWS Cognito or local mock store."""
        # 1. Live AWS Cognito
        if self.client and not settings.MOCK_COGNITO:
            try:
                user_attributes = [
                    {"Name": "email", "Value": email},
                ]
                # custom:role if configured in User Pool attributes
                try:
                    user_attributes.append({"Name": "custom:role", "Value": role})
                except Exception:
                    pass

                resp = self.client.sign_up(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username,
                    Password=password,
                    UserAttributes=user_attributes,
                )
                return {
                    "user_sub": resp.get("UserSub"),
                    "user_confirmed": resp.get("UserConfirmed", False),
                    "delivery_medium": resp.get("CodeDeliveryDetails", {}).get("DeliveryMedium", "EMAIL"),
                    "destination": resp.get("CodeDeliveryDetails", {}).get("Destination", email),
                }
            except ClientError as e:
                code = e.response["Error"]["Code"]
                msg = e.response["Error"]["Message"]
                if code == "UsernameExistsException":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An account with this username or email already exists.",
                    )
                if code in ("InvalidPasswordException", "InvalidParameterException"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=msg,
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"AWS Cognito sign up error: {msg}",
                )

        # 2. Local Mock Simulator
        # Check uniqueness
        for u in self._mock_users.values():
            if u["username"].lower() == username.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Username '{username}' is already taken.",
                )
            if u["email"].lower() == email.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{email}' is already registered.",
                )

        # Password basic check
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters.",
            )

        new_sub = str(uuid.uuid4())
        self._mock_users[username] = {
            "sub": new_sub,
            "username": username,
            "email": email,
            "password": password,
            "role": role,
            "confirmed": False,
            "confirmation_code": "123456",  # Demo code for instant testing
        }

        return {
            "user_sub": new_sub,
            "user_confirmed": False,
            "delivery_medium": "EMAIL",
            "destination": email,
            "demo_hint": "In mock mode, confirmation code is '123456'",
        }

    # ==========================================
    # 2. CONFIRM SIGN UP (EMAIL OTP)
    # ==========================================
    def confirm_sign_up(self, username: str, confirmation_code: str) -> bool:
        """Confirm user's registration using the received OTP code."""
        if self.client and not settings.MOCK_COGNITO:
            try:
                self.client.confirm_sign_up(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username,
                    ConfirmationCode=confirmation_code,
                )
                return True
            except ClientError as e:
                code = e.response["Error"]["Code"]
                msg = e.response["Error"]["Message"]
                if code == "CodeMismatchException":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid verification code. Please check and try again.",
                    )
                if code == "ExpiredCodeException":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verification code has expired. Please request a new code.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=msg,
                )

        # Mock Mode
        user = self._find_mock_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found.",
            )

        # Accept user's stored code or demo code "123456"
        if confirmation_code not in (user.get("confirmation_code"), "123456"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code. (Hint: use 123456 in demo mode)",
            )

        user["confirmed"] = True
        return True

    # ==========================================
    # 3. RESEND CONFIRMATION CODE
    # ==========================================
    def resend_confirmation_code(self, username: str) -> Dict[str, Any]:
        """Resend confirmation code to user's registered email."""
        if self.client and not settings.MOCK_COGNITO:
            try:
                resp = self.client.resend_confirmation_code(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username,
                )
                details = resp.get("CodeDeliveryDetails", {})
                return {
                    "delivery_medium": details.get("DeliveryMedium", "EMAIL"),
                    "destination": details.get("Destination", ""),
                }
            except ClientError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=e.response["Error"]["Message"],
                )

        # Mock Mode
        user = self._find_mock_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found.",
            )
        user["confirmation_code"] = "123456"
        return {
            "delivery_medium": "EMAIL",
            "destination": user["email"],
            "demo_hint": "New verification code is 123456",
        }

    # ==========================================
    # 4. INITIATE AUTH (LOGIN)
    # ==========================================
    def initiate_auth(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user credentials via Cognito USER_PASSWORD_AUTH flow
        or local mock validation. Returns access token, claims, and expiry.
        """
        if self.client and not settings.MOCK_COGNITO:
            try:
                resp = self.client.initiate_auth(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={
                        "USERNAME": username_or_email,
                        "PASSWORD": password,
                    },
                )
                auth_result = resp.get("AuthenticationResult", {})
                access_token = auth_result.get("AccessToken")
                id_token = auth_result.get("IdToken")
                expires_in = auth_result.get("ExpiresIn", 3600)

                # Decode unverified claims from ID/Access token to extract user info
                from jose import jwt
                claims = {}
                token_to_inspect = id_token or access_token
                if token_to_inspect:
                    try:
                        claims = jwt.get_unverified_claims(token_to_inspect)
                    except Exception:
                        pass

                return {
                    "access_token": access_token or id_token,
                    "token_type": "Bearer",
                    "expires_in": expires_in,
                    "claims": claims,
                }
            except ClientError as e:
                code = e.response["Error"]["Code"]
                msg = e.response["Error"]["Message"]
                if code in ("NotAuthorizedException", "UserNotFoundException"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect username/email or password.",
                    )
                if code == "UserNotConfirmedException":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account email is not verified yet. Please enter confirmation code.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=msg,
                )

        # Mock Mode Authentication
        user = self._find_mock_user(username_or_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found. Please register first or use 1-Click Demo.",
            )

        if user.get("password") != password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. (Default demo password is 'Password123!')",
            )

        if not user.get("confirmed", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account email is not verified yet. Please enter confirmation code '123456'.",
            )

        token = create_demo_access_token(
            sub=user["sub"],
            email=user["email"],
            username=user["username"],
            role=user.get("role", "user"),
        )

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 604800,
            "claims": {
                "sub": user["sub"],
                "email": user["email"],
                "cognito:username": user["username"],
                "username": user["username"],
                "custom:role": user.get("role", "user"),
            },
        }

    # ==========================================
    # 5. FORGOT PASSWORD & RESET
    # ==========================================
    def forgot_password(self, username_or_email: str) -> Dict[str, Any]:
        """Trigger password reset confirmation code to registered email."""
        if self.client and not settings.MOCK_COGNITO:
            try:
                resp = self.client.forgot_password(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username_or_email,
                )
                details = resp.get("CodeDeliveryDetails", {})
                return {
                    "delivery_medium": details.get("DeliveryMedium", "EMAIL"),
                    "destination": details.get("Destination", ""),
                }
            except ClientError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=e.response["Error"]["Message"],
                )

        # Mock Mode
        user = self._find_mock_user(username_or_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username_or_email}' not found.",
            )
        user["reset_code"] = "123456"
        return {
            "delivery_medium": "EMAIL",
            "destination": user["email"],
            "demo_hint": "Reset code is 123456 in demo mode.",
        }

    def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str,
    ) -> bool:
        """Complete password reset using received OTP and new password."""
        if self.client and not settings.MOCK_COGNITO:
            try:
                self.client.confirm_forgot_password(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username,
                    ConfirmationCode=confirmation_code,
                    Password=new_password,
                )
                return True
            except ClientError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=e.response["Error"]["Message"],
                )

        # Mock Mode
        user = self._find_mock_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found.",
            )
        if confirmation_code not in (user.get("reset_code"), "123456"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset code.",
            )
        user["password"] = new_password
        user["reset_code"] = None
        return True

    def _find_mock_user(self, username_or_email: str) -> Optional[Dict[str, Any]]:
        target = username_or_email.lower()
        for u in self._mock_users.values():
            if u["username"].lower() == target or u["email"].lower() == target:
                return u
        return None


cognito_service = CognitoService()
