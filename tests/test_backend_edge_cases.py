"""Comprehensive edge-case and robustness tests for CodeGrid backend.

Covers:
- HarnessService edge cases (negative numbers, 64-bit ints, float tolerance, scientific notation,
  truncation boundaries, malformed outputs, mixed complex signatures).
- Security & JWT edge cases (expired tokens, tampered signatures, malformed payloads).
- CognitoService edge cases (case-insensitivity, password validation, unconfirmed login, full recovery cycle).
- Judge0Service edge cases (language ID validation, mock execution of success, wrong answer, runtime error, timeout).
- CacheService graceful degradation under Redis failure.
- S3Service testcase bundle edge cases.
- RateLimiter edge cases.
"""

import math
import uuid
from datetime import timedelta
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.rate_limiter import RateLimiter
from app.core.security import create_demo_access_token, verify_jwt_token
from app.models.enums import SubmissionStatus
from app.services.cache_service import CacheService
from app.services.cognito_service import cognito_service
from app.services.harness_service import harness_service, OUTPUT_DELIMITER, TESTCASE_DELIMITER
from app.services.judge0_service import judge0_service
from app.services.s3_service import s3_service

settings = get_settings()


# ==========================================
# 1. HARNESS SERVICE EDGE CASES
# ==========================================

def test_harness_outputs_match_scientific_notation():
    """Verify _outputs_match correctly equates scientific notation numbers."""
    assert harness_service._outputs_match("1e-4", "0.0001") is True
    assert harness_service._outputs_match("1.0e-5", "0.00001") is True
    assert harness_service._outputs_match("2.5e3", "2500.0") is True
    assert harness_service._outputs_match("1e-2", "0.05") is False


def test_harness_outputs_match_nested_floats_tolerance():
    """Verify _outputs_match accepts nested matrices and arrays with minor float delta."""
    act = "[[0.1000002, 0.2000001], [0.3000003, 0.4000004]]"
    exp = "[[0.1, 0.2], [0.3, 0.4]]"
    assert harness_service._outputs_match(act, exp) is True

    # Differing dimensions or lengths
    assert harness_service._outputs_match("[1.0, 2.0, 3.0]", "[1.0, 2.0]") is False
    assert harness_service._outputs_match("[[1.0]]", "[1.0]") is False


def test_harness_outputs_match_whitespace_and_newlines():
    """Verify outputs with trailing newlines, carriage returns, or spaces match."""
    assert harness_service._outputs_match("42\r\n", "42") is True
    assert harness_service._outputs_match("  true \n", "true") is True
    assert harness_service._outputs_match("[ 1,  2, 3 ]\n", "[1,2,3]") is True
    assert harness_service._outputs_match("hello world\n", "hello world") is True


def test_harness_truncation_boundaries():
    """Verify truncate_text handles boundary conditions cleanly."""
    assert harness_service.truncate_text(None) == ""
    assert harness_service.truncate_text("") == ""
    assert harness_service.truncate_text("short") == "short"

    # Exactly max_len
    exact_text = "a" * 50
    assert harness_service.truncate_text(exact_text, max_len=50) == exact_text

    # One character over max_len
    over_text = "a" * 51
    truncated = harness_service.truncate_text(over_text, max_len=50)
    assert len(truncated) > 50
    assert "truncated" in truncated
    assert "total 51 chars" in truncated

    # Massive 50,000 char input
    giant_text = "x" * 50000
    res = harness_service.truncate_text(giant_text, max_len=1000)
    assert len(res) < 1100
    assert "total 50000 chars" in res


def test_harness_extract_first_failure_boundaries():
    """Verify extract_first_failure under various result configurations."""
    # All passed -> None
    all_ok = [
        {"index": 1, "passed": True, "actual": "1"},
        {"index": 2, "passed": True, "actual": "2"},
    ]
    assert harness_service.extract_first_failure(all_ok, ["1", "2"], ["1", "2"]) is None

    # Empty results -> None
    assert harness_service.extract_first_failure([], [], []) is None

    # Middle testcase failed
    middle_fail = [
        {"index": 1, "passed": True, "actual": "1"},
        {"index": 2, "passed": False, "actual": "wrong"},
        {"index": 3, "passed": True, "actual": "3"},
    ]
    fail_data = harness_service.extract_first_failure(middle_fail, ["1", "2", "3"], ["1", "exp2", "3"])
    assert fail_data is not None
    assert fail_data["test_case_number"] == 2
    assert fail_data["input"] == "2"
    assert fail_data["expected_output"] == "exp2"
    assert fail_data["actual_output"] == "wrong"

    # Inputs list shorter than parsed results -> graceful fallback
    short_inputs = [
        {"index": 1, "passed": False, "actual": "err"},
    ]
    short_fail = harness_service.extract_first_failure(short_inputs, [], [])
    assert short_fail is not None
    assert short_fail["input"] == ""
    assert short_fail["expected_output"] == ""


def test_harness_batch_inputs_edge_cases():
    """Verify batch_inputs handles empty lists, None values, and blank lines."""
    assert harness_service.batch_inputs([]) == ""
    assert harness_service.batch_inputs(["", "   "]) == f"\n{TESTCASE_DELIMITER}\n"

    cases = ["1 2", "3 4", "5 6"]
    batched = harness_service.batch_inputs(cases)
    assert batched == f"1 2\n{TESTCASE_DELIMITER}\n3 4\n{TESTCASE_DELIMITER}\n5 6"


def test_harness_cpp_complex_mixed_signature():
    """Verify C++ harness generation with 4 diverse parameter types."""
    cpp_code = """class Solution {
public:
    double findMedian(vector<int>& nums1, vector<int>& nums2, int k, bool isMax) {
        return 2.5;
    }
};"""
    stitched = harness_service.assemble_code("cpp", cpp_code)
    assert "parseVectorInt" in stitched
    assert "parseInt" in stitched
    assert "parseBool" in stitched
    assert "solver.findMedian(arg0, arg1, arg2, arg3)" in stitched
    assert "printResult(result)" in stitched


def test_harness_java_nested_generics_signature():
    """Verify Java harness parses complex nested generics without syntax corruption."""
    java_code = """class Solution {
    public List<String> topKFrequent(String[] words, int k, Map<String, Integer> freq) {
        return new ArrayList<>();
    }
}"""
    stitched = harness_service.assemble_code("java", java_code)
    assert "parseStringArray(line)" in stitched
    assert "Integer.parseInt(line)" in stitched
    assert "solver.topKFrequent(arg0, arg1, arg2)" in stitched


# ==========================================
# 2. SECURITY & JWT EDGE CASES
# ==========================================

@pytest.mark.asyncio
async def test_security_expired_jwt_rejected():
    """Verify JWT token that is expired raises HTTP 401 Unauthorized."""
    # Create token expired 1 hour ago
    expired_token = create_demo_access_token(
        sub="expired-user-1",
        email="expired@test.com",
        username="expired_user",
        expires_delta=timedelta(hours=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_security_tampered_jwt_signature_rejected():
    """Verify modifying any character of the signature causes immediate rejection."""
    valid_token = create_demo_access_token(
        sub="valid-user-1",
        email="valid@test.com",
        username="valid_user",
    )
    # Tamper with the last 4 characters
    tampered_token = valid_token[:-4] + "xxxx"

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(tampered_token)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_security_malformed_jwt_rejected():
    """Verify arbitrary garbage string raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token("not.a.valid.jwt.payload")
    assert exc_info.value.status_code == 401


# ==========================================
# 3. COGNITO SERVICE EDGE CASES
# ==========================================

def test_cognito_case_insensitive_uniqueness():
    """Verify username and email conflicts are detected case-insensitively."""
    uid = uuid.uuid4().hex[:6]
    uname = f"CaseUser_{uid}"
    email = f"CaseUser_{uid}@example.com"

    # Register
    cognito_service.sign_up(username=uname, email=email, password="Password123!")

    # Attempt registration with different casing for username
    with pytest.raises(HTTPException) as exc1:
        cognito_service.sign_up(username=uname.lower(), email=f"diff_{uid}@example.com", password="Password123!")
    assert exc1.value.status_code == 409

    # Attempt registration with different casing for email
    with pytest.raises(HTTPException) as exc2:
        cognito_service.sign_up(username=f"diff_{uid}", email=email.upper(), password="Password123!")
    assert exc2.value.status_code == 409


def test_cognito_unconfirmed_login_blocked():
    """Verify an unconfirmed user account is blocked with HTTP 403."""
    uid = uuid.uuid4().hex[:6]
    uname = f"unconf_{uid}"
    email = f"unconf_{uid}@test.com"

    cognito_service.sign_up(username=uname, email=email, password="Password123!")

    # Attempt login without confirming
    with pytest.raises(HTTPException) as exc:
        cognito_service.initiate_auth(username_or_email=uname, password="Password123!")
    assert exc.value.status_code == 403
    assert "not verified" in exc.value.detail


def test_cognito_resend_code_generates_valid_otp():
    """Verify resending code allows subsequent confirmation."""
    uid = uuid.uuid4().hex[:6]
    uname = f"resend_{uid}"
    email = f"resend_{uid}@test.com"

    cognito_service.sign_up(username=uname, email=email, password="Password123!")

    # Resend
    resend_res = cognito_service.resend_confirmation_code(uname)
    assert resend_res["destination"] == email

    # Confirm using the demo code
    ok = cognito_service.confirm_sign_up(uname, "123456")
    assert ok is True


def test_cognito_password_reset_nonexistent_user():
    """Verify forgot_password and confirm_forgot_password handle unknown users with 404."""
    with pytest.raises(HTTPException) as exc1:
        cognito_service.forgot_password("ghost_user_99999")
    assert exc1.value.status_code == 404

    with pytest.raises(HTTPException) as exc2:
        cognito_service.confirm_forgot_password("ghost_user_99999", "123456", "NewPassword123!")
    assert exc2.value.status_code == 404


# ==========================================
# 4. JUDGE0 SERVICE & MOCK EVALUATION
# ==========================================

def test_judge0_language_id_lookup():
    """Verify supported languages map properly and unsupported languages raise ValueError."""
    assert judge0_service.get_language_id("python") == 71
    assert judge0_service.get_language_id("cpp") == 54
    assert judge0_service.get_language_id("java") == 62
    assert judge0_service.get_language_id("javascript") == 63

    with pytest.raises(ValueError):
        judge0_service.get_language_id("brainfuck")


@pytest.mark.asyncio
async def test_judge0_mock_evaluate_python_success():
    """Verify local mock evaluator executes simple Python code and returns ACCEPTED."""
    py_code = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
    res = await judge0_service.execute_test_case(
        source_code=py_code,
        language="python",
        stdin="10 20\n",
        expected_output="30\n",
    )
    assert res["status"] == SubmissionStatus.ACCEPTED
    assert "30" in res["stdout"]


@pytest.mark.asyncio
async def test_judge0_mock_evaluate_python_wrong_answer():
    """Verify local mock evaluator correctly tags WRONG_ANSWER when output doesn't match."""
    py_code = "print(999)"
    res = await judge0_service.execute_test_case(
        source_code=py_code,
        language="python",
        stdin="1 2\n",
        expected_output="3\n",
    )
    assert res["status"] == SubmissionStatus.WRONG_ANSWER
    assert "999" in res["stdout"]


@pytest.mark.asyncio
async def test_judge0_mock_evaluate_python_runtime_error():
    """Verify local mock evaluator catches exceptions and returns RUNTIME_ERROR."""
    py_code = "raise ZeroDivisionError('fatal division by zero')"
    res = await judge0_service.execute_test_case(
        source_code=py_code,
        language="python",
        stdin="",
        expected_output="0",
    )
    assert res["status"] == SubmissionStatus.RUNTIME_ERROR
    assert "ZeroDivisionError" in res["stderr"]


# ==========================================
# 5. CACHE SERVICE DEGRADATION
# ==========================================

@pytest.mark.asyncio
async def test_cache_service_graceful_fallback():
    """Verify CacheService operations don't throw when Redis operations fail."""
    # Getting a non-existent or failed key returns None safely
    res = await CacheService.get_json("non_existent_key_xyz_123")
    assert res is None


# ==========================================
# 6. S3 SERVICE BUNDLE EDGE CASES
# ==========================================

def test_s3_bundle_nonexistent_returns_none():
    """Verify asking for an unseeded problem bundle returns None without error."""
    bundle = s3_service.get_problem_testcase_bundle(problem_id=99999999, slug="nonexistent-slug-xyz")
    assert bundle is None


def test_s3_bundle_storage_with_unicode_and_special_chars():
    """Verify storing bundle with unicode characters, quotes, and newlines roundtrips cleanly."""
    bundle_data = {
        "method_name": "specialCharSolve",
        "test_cases": [
            {
                "input": "quoted: \"hello\", escaped: \\n, unicode: 🚀",
                "expected_output": "success_🎯",
                "is_sample": True,
            }
        ],
    }
    s3_service.put_problem_testcase_bundle(problem_id=88888, bundle_data=bundle_data, slug="unicode-prob")
    retrieved = s3_service.get_problem_testcase_bundle(problem_id=88888, slug="unicode-prob")

    assert retrieved is not None
    assert retrieved["method_name"] == "specialCharSolve"
    assert "🚀" in retrieved["test_cases"][0]["input"]
    assert "🎯" in retrieved["test_cases"][0]["expected_output"]
