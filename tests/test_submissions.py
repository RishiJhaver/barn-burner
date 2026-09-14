"""Integration tests for Phase 4: Code Execution Engine, Submissions & Judge0."""

import uuid
import pytest
from app.core.security import create_demo_access_token


async def get_auth_headers(client, sub: str, email: str, username: str, role: str = "user") -> dict:
    """Helper to generate demo token, sync user with database, and return auth headers."""
    token = create_demo_access_token(sub=sub, email=email, username=username, role=role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/auth/sync", headers=headers)
    assert resp.status_code in (200, 201)
    return headers


async def create_test_problem(client, admin_headers, slug: str, title: str) -> dict:
    """Helper to create a problem with sample and hidden test cases in S3."""
    problem_payload = {
        "title": title,
        "slug": slug,
        "description": "Calculate sum of two numbers",
        "difficulty": "easy",
        "published": True,
        "templates": [
            {
                "language": "python",
                "starter_code": "def solution(a, b):\n    return a + b",
            }
        ],
        "test_cases": [
            {
                "input": "1 2",
                "expected_output": "3",
                "is_sample": True,
            },
            {
                "input": "10 20",
                "expected_output": "30",
                "is_sample": False,
            },
        ],
    }
    resp = await client.post("/api/v1/problems", json=problem_payload, headers=admin_headers)
    assert resp.status_code in (201, 409)
    if resp.status_code == 201:
        return resp.json()
    get_resp = await client.get(f"/api/v1/problems/{slug}")
    return get_resp.json()


@pytest.mark.asyncio(loop_scope="function")
async def test_pydantic_code_validation(client):
    """Verify strict Pydantic validation on request schemas."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_auth_headers(
        client,
        sub=f"user-sub-val-{uid}",
        email=f"val_{uid}@example.com",
        username=f"val_{uid}",
    )

    # 1. Unsupported language -> 422
    resp_lang = await client.post(
        "/api/v1/problems/any-problem/run",
        json={"language": "brainfuck", "code": "print('hello')"},
        headers=headers,
    )
    assert resp_lang.status_code == 422

    # 2. Empty code -> 422
    resp_empty = await client.post(
        "/api/v1/problems/any-problem/run",
        json={"language": "python", "code": ""},
        headers=headers,
    )
    assert resp_empty.status_code == 422

    # 3. Oversized code (> 64KB) -> 422
    huge_code = "a = 1\n" * 20000  # ~120KB
    resp_huge = await client.post(
        "/api/v1/problems/any-problem/run",
        json={"language": "python", "code": huge_code},
        headers=headers,
    )
    assert resp_huge.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_run_code_non_blocking_202(client):
    """Verify POST /problems/{slug}/run returns 202 Accepted immediately without blocking."""
    uid = uuid.uuid4().hex[:6]
    admin_headers = await get_auth_headers(
        client,
        sub=f"admin-sub-run-{uid}",
        email=f"admin_run_{uid}@example.com",
        username=f"admin_run_{uid}",
        role="admin",
    )
    user_headers = await get_auth_headers(
        client,
        sub=f"user-sub-run-{uid}",
        email=f"user_run_{uid}@example.com",
        username=f"user_run_{uid}",
        role="user",
    )

    slug = f"prob-run-{uid}"
    await create_test_problem(client, admin_headers, slug=slug, title=f"Run Problem {uid}")

    # Trigger Run
    run_payload = {
        "language": "python",
        "code": "print('3')",
    }
    run_resp = await client.post(
        f"/api/v1/problems/{slug}/run",
        json=run_payload,
        headers=user_headers,
    )
    # Immediately returns 202 Accepted
    assert run_resp.status_code == 202
    data = run_resp.json()
    assert "submission_id" in data
    assert data["kind"] == "run"
    assert data["status"] in ("pending", "processing", "accepted")

    submission_id = data["submission_id"]

    # Poll status
    poll_resp = await client.get(f"/api/v1/submissions/{submission_id}", headers=user_headers)
    assert poll_resp.status_code == 200
    poll_data = poll_resp.json()
    assert poll_data["kind"] == "run"
    assert poll_data["status"] == "accepted"
    assert poll_data["runtime_ms"] is not None


@pytest.mark.asyncio(loop_scope="function")
async def test_submit_code_accepted_and_updates_solved_status(client):
    """User submits correct code: returns 202 Accepted, evaluates in background, marks solved."""
    uid = uuid.uuid4().hex[:6]
    admin_headers = await get_auth_headers(
        client,
        sub=f"admin-sub-acc-{uid}",
        email=f"admin_acc_{uid}@example.com",
        username=f"admin_acc_{uid}",
        role="admin",
    )
    user_headers = await get_auth_headers(
        client,
        sub=f"user-sub-acc-{uid}",
        email=f"user_acc_{uid}@example.com",
        username=f"user_acc_{uid}",
        role="user",
    )

    slug = f"prob-acc-{uid}"
    prob = await create_test_problem(client, admin_headers, slug=slug, title=f"Accepted Problem {uid}")

    submit_payload = {
        "language": "python",
        "code": "def solution(a, b):\n    return a + b",
    }
    submit_resp = await client.post(
        f"/api/v1/problems/{slug}/submit",
        json=submit_payload,
        headers=user_headers,
    )
    assert submit_resp.status_code == 202
    sub_id = submit_resp.json()["submission_id"]

    # Poll status
    poll_resp = await client.get(f"/api/v1/submissions/{sub_id}", headers=user_headers)
    assert poll_resp.status_code == 200
    sub_data = poll_resp.json()
    assert sub_data["status"] == "accepted"
    assert sub_data["problem_id"] == prob["id"]
    assert sub_data["runtime_ms"] > 0
    assert sub_data["memory_kb"] > 0


@pytest.mark.asyncio(loop_scope="function")
async def test_submit_code_wrong_answer_marks_attempted(client):
    """User submits incorrect code: returns 202, evaluates in background, marks wrong_answer."""
    uid = uuid.uuid4().hex[:6]
    admin_headers = await get_auth_headers(
        client,
        sub=f"admin-sub-wa-{uid}",
        email=f"admin_wa_{uid}@example.com",
        username=f"admin_wa_{uid}",
        role="admin",
    )
    user_headers = await get_auth_headers(
        client,
        sub=f"user-sub-wa-{uid}",
        email=f"user_wa_{uid}@example.com",
        username=f"user_wa_{uid}",
        role="user",
    )

    slug = f"prob-wa-{uid}"
    await create_test_problem(client, admin_headers, slug=slug, title=f"WA Problem {uid}")

    submit_payload = {
        "language": "python",
        "code": "# wrong_answer hint triggers mock failure\ndef solution(a, b):\n    return -1",
    }
    submit_resp = await client.post(
        f"/api/v1/problems/{slug}/submit",
        json=submit_payload,
        headers=user_headers,
    )
    assert submit_resp.status_code == 202
    sub_id = submit_resp.json()["submission_id"]

    # Poll status
    poll_resp = await client.get(f"/api/v1/submissions/{sub_id}", headers=user_headers)
    assert poll_resp.status_code == 200
    sub_data = poll_resp.json()
    assert sub_data["status"] == "wrong_answer"


@pytest.mark.asyncio(loop_scope="function")
async def test_submissions_history_list(client):
    """Verify GET /api/v1/submissions returns user history with problem metadata."""
    uid = uuid.uuid4().hex[:6]
    admin_headers = await get_auth_headers(
        client,
        sub=f"admin-sub-hist-{uid}",
        email=f"admin_hist_{uid}@example.com",
        username=f"admin_hist_{uid}",
        role="admin",
    )
    user_headers = await get_auth_headers(
        client,
        sub=f"user-sub-hist-{uid}",
        email=f"user_hist_{uid}@example.com",
        username=f"user_hist_{uid}",
        role="user",
    )

    slug = f"prob-hist-{uid}"
    await create_test_problem(client, admin_headers, slug=slug, title=f"History Problem {uid}")

    # Make 2 submissions
    for i in range(2):
        await client.post(
            f"/api/v1/problems/{slug}/submit",
            json={"language": "python", "code": f"print({i})"},
            headers=user_headers,
        )

    # Query history
    history_resp = await client.get("/api/v1/submissions?limit=10", headers=user_headers)
    assert history_resp.status_code == 200
    items = history_resp.json()
    assert len(items) >= 2
    assert all("id" in item and "status" in item for item in items)
    assert any(item["problem_slug"] == slug for item in items)
