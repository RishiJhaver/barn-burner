"""Tests for problems, tags, Redis caching, and S3 storage."""

import uuid
import pytest
from app.core.security import create_demo_access_token
from app.services.cache_service import CacheService


async def get_auth_headers(client, sub: str, email: str, username: str, role: str = "user") -> dict:
    """Helper to generate demo token, sync user with database, and return auth headers."""
    token = create_demo_access_token(sub=sub, email=email, username=username, role=role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/auth/sync", headers=headers)
    assert resp.status_code in (200, 201)
    return headers


@pytest.mark.asyncio(loop_scope="function")
async def test_create_tag_and_list(client):
    """Test tag creation by admin and public listing."""
    tag_uid = uuid.uuid4().hex[:6]
    tag_name = f"Dynamic Programming {tag_uid}"
    tag_slug = f"dp-{tag_uid}"

    headers = await get_auth_headers(
        client,
        sub=f"admin-sub-tag-{tag_uid}",
        email=f"tagadmin_{tag_uid}@example.com",
        username=f"tagadmin_{tag_uid}",
        role="admin",
    )

    # Admin creates tag
    tag_payload = {"name": tag_name, "slug": tag_slug}
    resp = await client.post("/api/v1/tags", json=tag_payload, headers=headers)
    assert resp.status_code == 201
    tag_data = resp.json()
    assert tag_data["name"] == tag_name
    assert tag_data["slug"] == tag_slug
    assert "id" in tag_data

    # Duplicate tag returns 409
    dup_resp = await client.post("/api/v1/tags", json=tag_payload, headers=headers)
    assert dup_resp.status_code == 409

    # Public list tags
    list_resp = await client.get("/api/v1/tags")
    assert list_resp.status_code == 200
    tags = list_resp.json()
    assert any(t["slug"] == tag_slug for t in tags)


@pytest.mark.asyncio(loop_scope="function")
async def test_problem_admin_authorization(client):
    """Verify standard users cannot create problems."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"user-sub-problem-{uid}",
        email=f"user_prob_{uid}@example.com",
        username=f"user_prob_{uid}",
        role="user",
    )
    payload = {
        "title": f"Test Problem {uid}",
        "slug": f"test-prob-{uid}",
        "description": "Given an array...",
        "difficulty": "easy",
        "published": True,
    }

    # Unauthenticated -> 401
    unauth_resp = await client.post("/api/v1/problems", json=payload)
    assert unauth_resp.status_code == 401

    # Standard user -> 403
    user_resp = await client.post(
        "/api/v1/problems",
        json=payload,
        headers=headers,
    )
    assert user_resp.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_create_problem_with_templates_tags_s3(client):
    """Admin creates problem with code templates, tags, and S3-persisted test cases."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"admin-sub-full-{uid}",
        email=f"fulladmin_{uid}@example.com",
        username=f"fulladmin_{uid}",
        role="admin",
    )

    # 1. Create a tag first
    tag_resp = await client.post(
        "/api/v1/tags",
        json={"name": f"Array {uid}", "slug": f"array-{uid}"},
        headers=headers,
    )
    assert tag_resp.status_code == 201
    tag_id = tag_resp.json()["id"]

    # 2. Create problem
    slug = f"two-sum-{uid}"
    problem_payload = {
        "title": f"Two Sum {uid}",
        "slug": slug,
        "description": "Given an array of integers `nums` and an integer `target`...",
        "difficulty": "easy",
        "published": True,
        "tag_ids": [tag_id],
        "templates": [
            {
                "language": "python",
                "starter_code": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        pass",
            },
            {
                "language": "javascript",
                "starter_code": "function twoSum(nums, target) {\n    // your code\n}",
            },
        ],
        "test_cases": [
            {
                "input": "[2,7,11,15]\n9",
                "expected_output": "[0,1]",
                "is_sample": True,
            },
            {
                "input": "[3,2,4]\n6",
                "expected_output": "[1,2]",
                "is_sample": False,
            },
        ],
    }

    create_resp = await client.post("/api/v1/problems", json=problem_payload, headers=headers)
    assert create_resp.status_code == 201
    prob = create_resp.json()
    assert prob["title"] == f"Two Sum {uid}"
    assert prob["slug"] == slug
    assert len(prob["templates"]) == 2
    assert len(prob["sample_test_cases"]) == 1
    # Check sample testcase decoded text from S3
    assert prob["sample_test_cases"][0]["input"] == "[2,7,11,15]\n9"
    assert prob["sample_test_cases"][0]["expected_output"] == "[0,1]"


@pytest.mark.asyncio(loop_scope="function")
async def test_get_problem_by_slug_and_caching(client):
    """Verify problem retrieval by slug and Redis caching."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"admin-sub-cache-{uid}",
        email=f"cacheadmin_{uid}@example.com",
        username=f"cacheadmin_{uid}",
        role="admin",
    )

    slug = f"cache-problem-{uid}"
    create_resp = await client.post(
        "/api/v1/problems",
        json={
            "title": f"Cache Test {uid}",
            "slug": slug,
            "description": "Cache description",
            "difficulty": "medium",
            "published": True,
            "templates": [
                {"language": "python", "starter_code": "# code"}
            ],
            "test_cases": [
                {"input": "1 2", "expected_output": "3", "is_sample": True}
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201

    # First fetch by slug populates Redis cache
    resp = await client.get(f"/api/v1/problems/{slug}")
    assert resp.status_code == 200
    prob = resp.json()
    assert prob["slug"] == slug

    # Verify Redis cache has the key
    cache_key = CacheService.problem_detail_key(slug)
    cached = await CacheService.get_json(cache_key)
    assert cached is not None
    assert cached["slug"] == slug

    # Second fetch returns successfully from cache
    resp2 = await client.get(f"/api/v1/problems/{slug}")
    assert resp2.status_code == 200
    assert resp2.json()["title"] == f"Cache Test {uid}"


@pytest.mark.asyncio(loop_scope="function")
async def test_update_problem_and_cache_invalidation(client):
    """Admin updates problem title, verifying Redis cache invalidation."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"admin-sub-upd-{uid}",
        email=f"updadmin_{uid}@example.com",
        username=f"updadmin_{uid}",
        role="admin",
    )

    slug = f"update-problem-{uid}"
    create_resp = await client.post(
        "/api/v1/problems",
        json={
            "title": f"Original Title {uid}",
            "slug": slug,
            "description": "Original description",
            "difficulty": "hard",
            "published": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["id"]

    # Prime cache
    get_resp = await client.get(f"/api/v1/problems/{slug}")
    assert get_resp.status_code == 200

    # Patch title
    new_title = f"Updated Title {uid}"
    patch_resp = await client.patch(
        f"/api/v1/problems/{problem_id}",
        json={"title": new_title},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == new_title

    # Fetch by slug again, verify fresh updated title
    fresh_resp = await client.get(f"/api/v1/problems/{slug}")
    assert fresh_resp.status_code == 200
    assert fresh_resp.json()["title"] == new_title


@pytest.mark.asyncio(loop_scope="function")
async def test_keyset_pagination_and_filters(client):
    """Verify keyset pagination and filtering by difficulty."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"admin-sub-pg-{uid}",
        email=f"pgadmin_{uid}@example.com",
        username=f"pgadmin_{uid}",
        role="admin",
    )

    # Create 3 problems with difficulty 'medium'
    for i in range(1, 4):
        await client.post(
            "/api/v1/problems",
            json={
                "title": f"Problem Medium {uid} {i}",
                "slug": f"prob-med-{uid}-{i}",
                "description": f"Description {i}",
                "difficulty": "medium",
                "published": True,
            },
            headers=headers,
        )

    # Query list with difficulty filter
    resp_medium = await client.get("/api/v1/problems?difficulty=medium&limit=2")
    assert resp_medium.status_code == 200
    items = resp_medium.json()
    assert len(items) == 2
    assert all(p["difficulty"] == "medium" for p in items)

    # Keyset pagination using last_id
    last_id = items[-1]["id"]
    resp_next = await client.get(f"/api/v1/problems?difficulty=medium&limit=2&last_id={last_id}")
    assert resp_next.status_code == 200
    next_items = resp_next.json()
    assert len(next_items) >= 1
    assert next_items[0]["id"] < last_id


@pytest.mark.asyncio(loop_scope="function")
async def test_avatar_presigned_url(client):
    """Verify authenticated user can generate an avatar presigned URL."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"user-sub-av-{uid}",
        email=f"avuser_{uid}@example.com",
        username=f"avuser_{uid}",
        role="user",
    )

    resp = await client.post("/api/v1/users/me/avatar/presigned-url", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "key" in data
    assert data["key"].startswith("avatars/")
    assert data["expires_in"] == 3600
