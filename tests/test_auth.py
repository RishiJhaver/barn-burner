"""Integration tests for Phase 2: Authentication, User Sync, and RBAC."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthcheck(client: AsyncClient):
    """Verify application healthcheck probe."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mock_cognito"] is True


@pytest.mark.asyncio
async def test_generate_demo_token(client: AsyncClient):
    """Verify demo token generation for user and admin."""
    # Standard user token
    user_resp = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "user", "username": "alice", "email": "alice@example.com"},
    )
    assert user_resp.status_code == 200
    user_data = user_resp.json()
    assert "access_token" in user_data
    assert user_data["role"] == "user"
    assert user_data["claims"]["username"] == "alice"

    # Admin token
    admin_resp = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "admin", "username": "admin_bob", "email": "admin_bob@example.com"},
    )
    assert admin_resp.status_code == 200
    admin_data = admin_resp.json()
    assert admin_data["role"] == "admin"


@pytest.mark.asyncio
async def test_sync_new_user_and_idempotency(client: AsyncClient):
    """Verify syncing a user creates a row in PostgreSQL and is idempotent."""
    unique_id = str(uuid.uuid4())[:8]
    email = f"user_{unique_id}@example.com"
    username = f"user_{unique_id}"

    # 1. Generate token
    token_res = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "user", "username": username, "email": email},
    )
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Sync user (first time -> creates user)
    sync_res = await client.post("/api/v1/auth/sync", headers=headers)
    assert sync_res.status_code == 200
    user_data = sync_res.json()
    assert user_data["email"] == email
    assert user_data["username"] == username
    assert user_data["role"] == "user"
    user_id = user_data["id"]

    # 3. Sync user again (idempotent -> returns same user)
    sync_res2 = await client.post("/api/v1/auth/sync", headers=headers)
    assert sync_res2.status_code == 200
    assert sync_res2.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_my_profile(client: AsyncClient):
    """Verify authenticated user can fetch their profile."""
    unique_id = str(uuid.uuid4())[:8]
    email = f"profile_{unique_id}@example.com"
    username = f"profile_{unique_id}"

    # Generate token & sync
    token_res = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "user", "username": username, "email": email},
    )
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/auth/sync", headers=headers)

    # Fetch profile
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
    assert me_res.json()["username"] == username


@pytest.mark.asyncio
async def test_unauthenticated_and_invalid_token_rejected(client: AsyncClient):
    """Verify 401 Unauthorized for missing or invalid tokens."""
    # No token
    res1 = await client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    # Invalid/garbage token
    res2 = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.garbage.token"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_rbac_admin_guard(client: AsyncClient):
    """Verify RBAC: standard user gets 403 Forbidden, admin gets 200 OK."""
    unique_id = str(uuid.uuid4())[:8]

    # 1. Standard user
    user_token_res = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "user", "username": f"std_{unique_id}", "email": f"std_{unique_id}@example.com"},
    )
    user_headers = {"Authorization": f"Bearer {user_token_res.json()['access_token']}"}
    await client.post("/api/v1/auth/sync", headers=user_headers)

    user_admin_res = await client.get("/api/v1/auth/admin-check", headers=user_headers)
    assert user_admin_res.status_code == 403
    assert "Admin privileges required" in user_admin_res.json()["detail"]

    # 2. Admin user
    admin_token_res = await client.post(
        "/api/v1/auth/demo-token",
        json={"role": "admin", "username": f"adm_{unique_id}", "email": f"adm_{unique_id}@example.com"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_token_res.json()['access_token']}"}
    await client.post("/api/v1/auth/sync", headers=admin_headers)

    admin_check_res = await client.get("/api/v1/auth/admin-check", headers=admin_headers)
    assert admin_check_res.status_code == 200
    assert admin_check_res.json()["status"] == "authorized"
    assert admin_check_res.json()["role"] == "admin"
