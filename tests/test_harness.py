"""Unit and integration tests for LeetCode-style Test Harness and Single-Call Execution."""

import uuid
import pytest
from httpx import AsyncClient
from app.services.harness_service import harness_service, OUTPUT_DELIMITER, TESTCASE_DELIMITER


def test_harness_custom_driver_substitution():
    """Verify custom driver replaces {{USER_CODE}} with user solution."""
    custom_driver = """#include <iostream>
// {{USER_CODE}}

int main() {
    Solution s;
    std::cout << s.add(1, 2) << std::endl;
    return 0;
}"""
    user_code = """class Solution {
public:
    int add(int a, int b) { return a + b; }
};"""

    stitched = harness_service.assemble_code("cpp", user_code, custom_driver)
    assert "class Solution" in stitched
    assert "int add(int a, int b)" in stitched
    assert "// {{USER_CODE}}" not in stitched
    assert "int main()" in stitched


def test_harness_cpp_largest_overlap_generation():
    """Verify C++ Solution class automatically generates main() calling solver.largestOverlap(arg0, arg1)."""
    user_code = """class Solution {
public:
    int largestOverlap(vector<vector<int>>& img1, vector<vector<int>>& img2) {
        return 3;
    }
};"""

    stitched = harness_service.assemble_code("cpp", user_code)
    assert "parseMatrixInt" in stitched
    assert "solver.largestOverlap(arg0, arg1)" in stitched
    assert "printResult(result)" in stitched
    assert OUTPUT_DELIMITER in stitched
    assert TESTCASE_DELIMITER in stitched


def test_harness_python_default_wrapper():
    """Verify Python Solution class gets wrapped with LeetCode testcase dispatcher."""
    user_code = """class Solution:
    def largestOverlap(self, img1: List[List[int]], img2: List[List[int]]) -> int:
        return 3"""

    stitched = harness_service.assemble_code("python", user_code)
    assert "class Solution:" in stitched
    assert "_run_harness()" in stitched
    assert TESTCASE_DELIMITER in stitched
    assert OUTPUT_DELIMITER in stitched


def test_harness_java_largest_overlap_generation():
    """Verify Java Solution class gets wrapped in Main class calling solver.largestOverlap(arg0, arg1)."""
    user_code = """class Solution {
    public int largestOverlap(int[][] img1, int[][] img2) {
        return 3;
    }
}"""

    stitched = harness_service.assemble_code("java", user_code)
    assert "public class Main" in stitched
    assert "parse2DIntArray" in stitched
    assert "solver.largestOverlap(arg0, arg1)" in stitched
    assert OUTPUT_DELIMITER in stitched


def test_harness_js_largest_overlap_generation():
    """Verify JavaScript var function gets wrapped with Node.js fs reader and executor."""
    user_code = """/**
 * @param {number[][]} img1
 * @param {number[][]} img2
 * @return {number}
 */
var largestOverlap = function(img1, img2) {
    return 3;
};"""

    stitched = harness_service.assemble_code("javascript", user_code)
    assert "fs.readFileSync" in stitched
    assert "JSON.parse" in stitched
    assert "solveFn.apply" in stitched
    assert OUTPUT_DELIMITER in stitched


def test_harness_output_parsing_and_json_matching():
    """Verify outputs are matched and normalized (including JSON lists)."""
    stdout = f"[0, 1]\n{OUTPUT_DELIMITER}\n42\n{OUTPUT_DELIMITER}\nwrong\n{OUTPUT_DELIMITER}\n"
    expected = ["[0,1]", "42", "correct"]

    results = harness_service.parse_outputs(stdout, expected)
    assert len(results) == 3
    assert results[0]["passed"] is True   # [0, 1] matches [0,1]
    assert results[1]["passed"] is True   # 42 matches 42
    assert results[2]["passed"] is False  # wrong != correct


@pytest.mark.asyncio(loop_scope="function")
async def test_single_call_execution_with_driver_code(client: AsyncClient):
    """End-to-end integration test: Problem with driver code evaluates all test cases in one call."""
    uid = uuid.uuid4().hex[:6]

    # 1. Get tokens
    admin_resp = await client.post(
        "/api/v1/auth/demo-token",
        json={"sub": f"admin-harness-{uid}", "email": f"admin_{uid}@test.com", "username": f"adm_{uid}", "role": "admin"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_resp.json()['access_token']}"}

    user_resp = await client.post(
        "/api/v1/auth/demo-token",
        json={"sub": f"user-harness-{uid}", "email": f"user_{uid}@test.com", "username": f"usr_{uid}", "role": "user"},
    )
    user_headers = {"Authorization": f"Bearer {user_resp.json()['access_token']}"}

    # 2. Create problem with custom driver_code in template
    slug = f"prob-harness-{uid}"
    problem_payload = {
        "title": f"Harness Problem {uid}",
        "slug": slug,
        "description": "Calculate largest overlap",
        "difficulty": "medium",
        "published": True,
        "templates": [
            {
                "language": "python",
                "starter_code": "class Solution:\n    def solve(self, a: int, b: int) -> int:\n        pass",
                "driver_code": "# Hidden driver\n# {{USER_CODE}}\n# End driver",
            }
        ],
        "test_cases": [
            {"input": "1 2\n", "expected_output": "3\n", "is_sample": True},
            {"input": "10 20\n", "expected_output": "30\n", "is_sample": False},
        ],
    }
    create_resp = await client.post("/api/v1/problems", json=problem_payload, headers=admin_headers)
    assert create_resp.status_code == 201

    # 3. User submits LeetCode Solution class
    submit_payload = {
        "language": "python",
        "code": "class Solution:\n    def solve(self, a: int, b: int) -> int:\n        return a + b",
    }
    sub_resp = await client.post(f"/api/v1/problems/{slug}/submit", json=submit_payload, headers=user_headers)
    assert sub_resp.status_code == 202
    sub_id = sub_resp.json()["submission_id"]

    # 4. Poll verdict
    poll_resp = await client.get(f"/api/v1/submissions/{sub_id}", headers=user_headers)
    assert poll_resp.status_code == 200
    sub_data = poll_resp.json()
    assert sub_data["status"] == "accepted"
    assert sub_data["total_test_cases"] == 2
    assert sub_data["passed_test_cases"] == 2
