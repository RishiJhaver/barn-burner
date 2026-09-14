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
    try:
        admin_resp = await client.post(
            "/api/v1/auth/demo-token",
            json={"sub": f"admin-harness-{uid}", "email": f"admin_{uid}@test.com", "username": f"adm_{uid}", "role": "admin"},
        )
    except Exception as exc:
        pytest.skip(f"Database offline, skipping integration test: {exc}")
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
    try:
        create_resp = await client.post("/api/v1/problems", json=problem_payload, headers=admin_headers)
    except Exception as exc:
        pytest.skip(f"Database offline, skipping integration test: {exc}")
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


def test_harness_method_name_support():
    """Verify specifying method_name injects targeted method call in Python and C++."""
    py_code = """class Solution:
    def helper(self): return 0
    def largestOverlap(self, img1: List[List[int]], img2: List[List[int]]) -> int: return 3
"""
    stitched_py = harness_service.assemble_code("python", py_code, method_name="largestOverlap")
    assert '"largestOverlap"' in stitched_py

    cpp_code = """class Solution {
public:
    int helper() { return 0; }
    int largestOverlap(vector<vector<int>>& img1, vector<vector<int>>& img2) { return 3; }
};"""
    stitched_cpp = harness_service.assemble_code("cpp", cpp_code, method_name="largestOverlap")
    assert "solver.largestOverlap(" in stitched_cpp


def test_harness_extract_first_failure_and_truncation():
    """Verify first failing test case is extracted with safe truncation."""
    parsed_results = [
        {"index": 1, "passed": True, "actual": "3", "expected": "3"},
        {"index": 2, "passed": False, "actual": "99", "expected": "42"},
        {"index": 3, "passed": False, "actual": "0", "expected": "1"},
    ]
    inputs = ["[1, 2]", "[3, 4]", "[5, 6]"]
    expected = ["3", "42", "1"]

    failure = harness_service.extract_first_failure(parsed_results, inputs, expected)
    assert failure is not None
    assert failure["test_case_number"] == 2
    assert failure["total_test_cases"] == 3
    assert failure["input"] == "[3, 4]"
    assert failure["expected_output"] == "42"
    assert failure["actual_output"] == "99"

    # Verify truncation helper
    giant_text = "a" * 2000
    truncated = harness_service.truncate_text(giant_text, max_len=50)
    assert len(truncated) < 150
    assert "truncated" in truncated


def test_s3_bundle_storage_and_retrieval():
    """Verify S3 testcase bundle storing and retrieval works."""
    from app.services.s3_service import s3_service
    bundle_data = {
        "method_name": "largestOverlap",
        "test_cases": [
            {
                "input": "[[1,1,0],[0,1,0],[0,1,0]]\n[[0,0,0],[0,1,1],[0,0,1]]",
                "expected_output": "3",
                "is_sample": True,
            }
        ],
    }

    s3_service.put_problem_testcase_bundle(problem_id=9999, bundle_data=bundle_data, slug="test-bundle-slug")
    retrieved = s3_service.get_problem_testcase_bundle(problem_id=9999, slug="test-bundle-slug")
    assert retrieved is not None
    assert retrieved["method_name"] == "largestOverlap"
    assert len(retrieved["test_cases"]) == 1
    assert retrieved["test_cases"][0]["expected_output"] == "3"


def test_bug1_stdin_desync_on_unmatched_signature():
    """Verify C++ and Java harnesses drain stdin to boundary when signature fails to match."""
    # C++ unmatched signature
    cpp_code = "class Solution { public: /* no method */ };"
    stitched_cpp = harness_service.assemble_code("cpp", cpp_code, method_name="nonExistent")
    assert "TESTCASE_DELIMITER" in stitched_cpp or TESTCASE_DELIMITER in stitched_cpp
    assert "Method signature not matched" in stitched_cpp
    assert "while (cin.peek() != EOF" in stitched_cpp

    # Java unmatched signature
    java_code = "class Solution { /* no method */ }"
    stitched_java = harness_service.assemble_code("java", java_code, method_name="nonExistent")
    assert "reader.readLine()" in stitched_java
    assert "Method signature not matched" in stitched_java


def test_bug2_java_generic_parameters_bracket_splitting():
    """Verify Java method with generic parameters (e.g. Map<String, Integer>) is parsed correctly."""
    java_code = """class Solution {
    public int solve(Map<String, Integer> counts, List<String> words, int k) {
        return k;
    }
}"""
    stitched = harness_service.assemble_code("java", java_code)
    # Should produce arg0, arg1, arg2 (3 args, not 4 from splitting on inner comma)
    assert "solver.solve(arg0, arg1, arg2)" in stitched
    assert "parseListString" in stitched


def test_bug3_type_parsing_and_fallback():
    """Verify C++ and Java extended type parsers and safe fallback declarations."""
    # C++ long long, char, float
    cpp_code = """class Solution {
public:
    long long process(long long a, char c, float f, vector<long long>& vec) {
        return a;
    }
};"""
    stitched_cpp = harness_service.assemble_code("cpp", cpp_code)
    assert "parseLongLong(line)" in stitched_cpp
    assert "parseChar(line)" in stitched_cpp
    assert "parseFloat(line)" in stitched_cpp
    assert "parseVectorLong(line)" in stitched_cpp

    # Java long, char, float, List<Integer>
    java_code = """class Solution {
    public long process(long a, char c, float f, List<Integer> list) {
        return a;
    }
}"""
    stitched_java = harness_service.assemble_code("java", java_code)
    assert "Long.parseLong(line)" in stitched_java
    assert "parseChar(line)" in stitched_java
    assert "Float.parseFloat(line)" in stitched_java
    assert "parseListInt(line)" in stitched_java


def test_bug4_zero_arg_void_methods():
    """Verify zero-argument void methods in C++ and Java do not crash generator with IndexError."""
    cpp_code = """class Solution {
public:
    void solve() {
    }
};"""
    stitched_cpp = harness_service.assemble_code("cpp", cpp_code)
    assert "solver.solve();" in stitched_cpp
    assert 'cout << "null";' in stitched_cpp

    java_code = """class Solution {
    public void solve() {
    }
}"""
    stitched_java = harness_service.assemble_code("java", java_code)
    assert "solver.solve();" in stitched_java
    assert 'System.out.print("null");' in stitched_java


def test_bug5_python_tuple_json_serialization():
    """Verify Python harness JSON-serializes tuple return values as arrays."""
    py_code = """class Solution:
    def twoSum(self, nums: List[int]) -> Tuple[int, int]:
        return (0, 1)
"""
    stitched = harness_service.assemble_code("python", py_code)
    assert "isinstance(res, (list, dict, bool, tuple))" in stitched


def test_bug6_js_template_literal_injection():
    """Verify JavaScript user code with template literal characters cannot inject or break harness."""
    malicious_user_code = "var solve = function(x) { const msg = `hello ${x}`; return msg; };"
    stitched = harness_service.assemble_code("javascript", malicious_user_code)
    # The user code should NOT be embedded inside a template literal like `${user_code}`
    assert "const fallbackName = \"solve\";" in stitched
    assert "const fnMatch = `" not in stitched


def test_bug7_float_tolerance_in_outputs_match():
    """Verify _outputs_match supports floating-point tolerance for scalar and nested numbers."""
    # Scalar floats within 1e-5
    assert harness_service._outputs_match("3.1415926", "3.14159") is True
    assert harness_service._outputs_match("0.5000001", "0.5") is True
    # Scalar floats outside tolerance
    assert harness_service._outputs_match("3.14", "3.15") is False

    # JSON nested floats
    assert harness_service._outputs_match("[1.000001, 2.0]", "[1.0, 2.0]") is True
    assert harness_service._outputs_match("[1.5, 2.0]", "[1.0, 2.0]") is False


def test_bug8_python_boolean_case_insensitivity():
    """Verify Python harness helper parses 'True', 'False', 'true', 'false', and Python lists."""
    py_code = """class Solution:
    def solve(self, flag: bool) -> bool:
        return flag
"""
    stitched = harness_service.assemble_code("python", py_code)
    assert 'raw.lower() == "true"' in stitched
    assert 'raw.lower() == "false"' in stitched
    assert "ast.literal_eval" in stitched

    # Execute _parse_arg from stitched code in a sandbox namespace to test actual runtime behavior
    ns = {}
    exec(compile(stitched, "<test_harness>", "exec"), ns)
    parse_fn = ns["_parse_arg"]

    assert parse_fn("True") is True
    assert parse_fn("true") is True
    assert parse_fn("False") is False
    assert parse_fn("false") is False
    assert parse_fn("[True, False]") == [True, False]
    assert parse_fn("(1, 2)") == (1, 2)


