"""Integration tests for enhanced submissions history filters and user stats."""

import uuid
import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, role: str = "user") -> tuple[dict, str]:
    uid = uuid.uuid4().hex[:6]
    sub = f"sub-{role}-{uid}"
    username = f"{role}_{uid}"
    email = f"{username}@example.com"

    resp = await client.post(
        "/api/v1/auth/demo-token",
        json={"sub": sub, "email": email, "username": username, "role": role},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


async def create_problem(client: AsyncClient, admin_headers: dict, difficulty: str = "easy") -> str:
    slug = f"prob-hist-{uuid.uuid4().hex[:6]}"
    payload = {
        "title": f"Problem {slug}",
        "slug": slug,
        "description": "Test description",
        "difficulty": difficulty,
        "published": True,
        "test_cases": [
            {
                "input": "1 2\n",
                "expected_output": "3\n",
                "is_sample": True,
            }
        ],
    }
    resp = await client.post("/api/v1/problems", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return slug


@pytest.mark.asyncio(loop_scope="function")
async def test_submissions_filtering_and_pagination(client):
    """Test filtering submissions by problem_slug, language, status, and pagination."""
    admin_headers, _ = await get_auth_headers(client, role="admin")
    user_headers, _ = await get_auth_headers(client, role="user")

    slug_a = await create_problem(client, admin_headers, difficulty="easy")
    slug_b = await create_problem(client, admin_headers, difficulty="medium")

    # Submit python to slug_a (accepted)
    await client.post(
        f"/api/v1/problems/{slug_a}/submit",
        json={"language": "python", "code": "def solution(a, b): return a + b"},
        headers=user_headers,
    )
    # Submit python to slug_a (wrong_answer)
    await client.post(
        f"/api/v1/problems/{slug_a}/submit",
        json={"language": "python", "code": "# wrong_answer\ndef solution(a, b): return -1"},
        headers=user_headers,
    )
    # Submit cpp to slug_b
    await client.post(
        f"/api/v1/problems/{slug_b}/submit",
        json={"language": "cpp", "code": "int main() { return 0; }"},
        headers=user_headers,
    )

    # 1. Filter by slug_a
    resp_a = await client.get(f"/api/v1/submissions?problem_slug={slug_a}", headers=user_headers)
    assert resp_a.status_code == 200
    assert resp_a.headers["X-Total-Count"] == "2"
    items_a = resp_a.json()
    assert len(items_a) == 2
    assert all(i["problem_slug"] == slug_a for i in items_a)

    # 2. Filter by language=cpp
    resp_cpp = await client.get("/api/v1/submissions?language=cpp", headers=user_headers)
    assert resp_cpp.status_code == 200
    assert resp_cpp.headers["X-Total-Count"] == "1"
    items_cpp = resp_cpp.json()
    assert len(items_cpp) == 1
    assert items_cpp[0]["language"] == "cpp"

    # 3. Test pagination: limit=1, offset=0 and offset=1
    resp_page1 = await client.get("/api/v1/submissions?limit=1&offset=0", headers=user_headers)
    assert resp_page1.status_code == 200
    assert len(resp_page1.json()) == 1
    assert resp_page1.headers["X-Total-Count"] == "3"

    resp_page2 = await client.get("/api/v1/submissions?limit=1&offset=1", headers=user_headers)
    assert resp_page2.status_code == 200
    assert len(resp_page2.json()) == 1
    # Check that page 1 and page 2 items are different
    assert resp_page1.json()[0]["id"] != resp_page2.json()[0]["id"]


@pytest.mark.asyncio(loop_scope="function")
async def test_user_coding_stats_endpoint(client):
    """Test GET /api/v1/submissions/stats aggregates totals, difficulty counts, and acceptance rate."""
    admin_headers, _ = await get_auth_headers(client, role="admin")
    user_headers, _ = await get_auth_headers(client, role="user")

    slug_easy = await create_problem(client, admin_headers, difficulty="easy")
    slug_medium = await create_problem(client, admin_headers, difficulty="medium")

    # Solve easy problem (accepted)
    resp_easy = await client.post(
        f"/api/v1/problems/{slug_easy}/submit",
        json={"language": "python", "code": "def solution(): return 1"},
        headers=user_headers,
    )
    assert resp_easy.status_code == 202
    sub_easy_id = resp_easy.json()["submission_id"]
    await client.get(f"/api/v1/submissions/{sub_easy_id}", headers=user_headers)

    # Fail medium problem (wrong_answer)
    resp_med = await client.post(
        f"/api/v1/problems/{slug_medium}/submit",
        json={"language": "python", "code": "# wrong_answer\ndef solution(): return 0"},
        headers=user_headers,
    )
    assert resp_med.status_code == 202
    sub_med_id = resp_med.json()["submission_id"]
    await client.get(f"/api/v1/submissions/{sub_med_id}", headers=user_headers)

    stats_resp = await client.get("/api/v1/submissions/stats", headers=user_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()

    assert stats["total_submissions"] == 2
    assert stats["accepted_submissions"] == 1
    assert stats["acceptance_rate"] == 50.0
    assert stats["easy_solved"] == 1
    assert stats["medium_solved"] == 0
    assert stats["hard_solved"] == 0
    assert stats["total_solved"] == 1
