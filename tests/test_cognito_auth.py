"""Tests for AWS Cognito Authentication & Authorization Service and Endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.cognito_service import cognito_service


@pytest.mark.asyncio
async def test_cognito_service_direct_mock_flow():
    """Verify CognitoService registration, confirmation, login, and reset in mock mode."""
    uname = "test_coder_99"
    email = "test99@example.com"
    pwd = "MySecretPassword123!"

    # 1. Sign Up
    signup_res = cognito_service.sign_up(username=uname, email=email, password=pwd, role="user")
    assert signup_res["user_confirmed"] is False
    assert signup_res["destination"] == email

    # 2. Duplicate registration check
    with pytest.raises(Exception):
        cognito_service.sign_up(username=uname, email=email, password=pwd)

    # 3. Confirm Sign Up
    confirmed = cognito_service.confirm_sign_up(username=uname, confirmation_code="123456")
    assert confirmed is True

    # 4. Login
    auth_res = cognito_service.initiate_auth(username_or_email=uname, password=pwd)
    assert "access_token" in auth_res
    assert auth_res["token_type"] == "Bearer"
    assert auth_res["claims"]["username"] == uname
    assert auth_res["claims"]["email"] == email

    # 5. Wrong password check
    with pytest.raises(Exception):
        cognito_service.initiate_auth(username_or_email=uname, password="WrongPassword!")

    # 6. Forgot Password
    forgot_res = cognito_service.forgot_password(username_or_email=uname)
    assert forgot_res["delivery_medium"] == "EMAIL"

    # 7. Confirm Forgot Password
    reset_ok = cognito_service.confirm_forgot_password(
        username=uname,
        confirmation_code="123456",
        new_password="NewPassword456!",
    )
    assert reset_ok is True

    # 8. Login with new password
    auth_res_new = cognito_service.initiate_auth(username_or_email=uname, password="NewPassword456!")
    assert "access_token" in auth_res_new


@pytest.mark.asyncio
async def test_auth_api_config_endpoint():
    """Verify GET /api/v1/auth/config returns authentication mode settings."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "mock_cognito" in data
        assert "aws_region" in data
        assert "user_pool_id" in data


@pytest.mark.asyncio
async def test_auth_api_login_endpoint():
    """Verify POST /api/v1/auth/login works with predefined mock demo users."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_payload = {
            "username_or_email": "alex_coder",
            "password": "Password123!",
        }
        resp = await client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["username"] == "alex_coder"
        assert data["role"] == "user"


@pytest.mark.asyncio
async def test_auth_api_admin_login_and_rbac():
    """Verify Admin login gets admin token and accesses RBAC protected /admin-check."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login as Admin
        admin_login = {
            "username_or_email": "elena_admin",
            "password": "Password123!",
        }
        resp = await client.post("/api/v1/auth/login", json=admin_login)
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        role = resp.json()["role"]
        assert role == "admin"

        # 2. Call /admin-check with token
        headers = {"Authorization": f"Bearer {token}"}
        check_resp = await client.get("/api/v1/auth/admin-check", headers=headers)
        assert check_resp.status_code == 200
        assert check_resp.json()["status"] == "authorized"
        assert check_resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_auth_api_user_forbidden_on_admin_check():
    """Verify standard Coder user gets 403 Forbidden on /admin-check."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login as Coder
        user_login = {
            "username_or_email": "alex_coder",
            "password": "Password123!",
        }
        resp = await client.post("/api/v1/auth/login", json=user_login)
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # 2. Call /admin-check with coder token -> 403 Forbidden
        headers = {"Authorization": f"Bearer {token}"}
        check_resp = await client.get("/api/v1/auth/admin-check", headers=headers)
        assert check_resp.status_code == 403
