import asyncio
from app.services.judge0_service import judge0_service
from app.services.harness_service import harness_service
from app.models.enums import SubmissionStatus

async def test():
    print("--- 1. Testing 'return \"hello world\"' for Trapping Rain Water ---")
    user_code = """class Solution:
    def trap(self, height: List[int]) -> int:
        return "hello world"
"""
    assembled = harness_service.assemble_code("python", user_code)
    stdin = harness_service.batch_inputs(["[0,1,0,2,1,0,1,3,2,1,2,1]", "[4,2,0,3,2,5]"])
    expected_outputs = ["6", "9"]
    batched_expected = harness_service.batch_inputs(expected_outputs)

    res = await judge0_service.execute_test_case(
        source_code=assembled,
        language="python",
        stdin=stdin,
        expected_output=batched_expected,
    )
    print("Execution status:", res["status"])
    print("Stdout from Python:", repr(res["stdout"]))
    print("Stderr from Python:", repr(res["stderr"]))

    parsed = harness_service.parse_outputs(res["stdout"], expected_outputs)
    print("Parsed outputs:")
    for p in parsed:
        print(f"  Test #{p['index']}: Passed={p['passed']}, Actual={repr(p['actual'])}, Expected={repr(p['expected'])}")

    passed_count = sum(1 for p in parsed if p["passed"])
    verdict = SubmissionStatus.ACCEPTED if passed_count == len(expected_outputs) else SubmissionStatus.WRONG_ANSWER
    print("FINAL VERDICT:", verdict.value)
    assert verdict == SubmissionStatus.WRONG_ANSWER, "Should have been WRONG_ANSWER!"

    print("\n--- 2. Testing Syntax Error 'hello world' ---")
    invalid_code = "hello world invalid syntax"
    assembled_invalid = harness_service.assemble_code("python", invalid_code)
    res_err = await judge0_service.execute_test_case(
        source_code=assembled_invalid,
        language="python",
        stdin=stdin,
        expected_output=batched_expected,
    )
    print("Execution status for syntax error:", res_err["status"])
    print("Compile/Syntax error message:", repr(res_err["compile_output"]))
    assert res_err["status"] == SubmissionStatus.COMPILATION_ERROR, "Should have been COMPILATION_ERROR!"

    print("\n--- 3. Testing Correct Solution for Trapping Rain Water ---")
    correct_code = """class Solution:
    def trap(self, height: List[int]) -> int:
        if not height:
            return 0
        l, r = 0, len(height) - 1
        left_max, right_max = height[l], height[r]
        ans = 0
        while l < r:
            if left_max < right_max:
                l += 1
                left_max = max(left_max, height[l])
                ans += left_max - height[l]
            else:
                r -= 1
                right_max = max(right_max, height[r])
                ans += right_max - height[r]
        return ans
"""
    assembled_correct = harness_service.assemble_code("python", correct_code)
    res_correct = await judge0_service.execute_test_case(
        source_code=assembled_correct,
        language="python",
        stdin=stdin,
        expected_output=batched_expected,
    )
    parsed_correct = harness_service.parse_outputs(res_correct["stdout"], expected_outputs)
    for p in parsed_correct:
        print(f"  Test #{p['index']}: Passed={p['passed']}, Actual={repr(p['actual'])}, Expected={repr(p['expected'])}")
    passed_correct_count = sum(1 for p in parsed_correct if p["passed"])
    verdict_correct = SubmissionStatus.ACCEPTED if passed_correct_count == len(expected_outputs) else SubmissionStatus.WRONG_ANSWER
    print("FINAL VERDICT FOR CORRECT SOLUTION:", verdict_correct.value)
    assert verdict_correct == SubmissionStatus.ACCEPTED, "Should have been ACCEPTED!"

    print("\nALL COMPARISON LOGIC TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test())
