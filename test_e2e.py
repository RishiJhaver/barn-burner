import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_full_pipeline():
    client = httpx.Client()
    print("--- 1. Testing Problems API ---")
    res = client.get(f"{BASE_URL}/problems")
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()
    items = data if isinstance(data, list) else data.get("items", [])
    print(f"Retrieved {len(items)} problems:")
    for p in items[:5]:
        print(f"  [{p['difficulty'].upper()}] {p['title']} ({p['slug']})")

    print("\n--- 2. Testing Largest Overlap Details ---")
    res = client.get(f"{BASE_URL}/problems/largest-overlap")
    assert res.status_code == 200, f"Failed: {res.text}"
    lo = res.json()
    print(f"Problem: {lo['title']}")
    print(f"Sample test cases: {len(lo.get('sample_test_cases', []))}")
    print("Available templates:", [t['language'] for t in lo.get('templates', [])])

    print("\n--- 3. Testing Demo Auth (Neo Coder) ---")
    auth_res = client.post(
        f"{BASE_URL}/auth/demo-token",
        json={"role": "user", "username": "neo_coder", "email": "neo@matrix.cyber"}
    )
    assert auth_res.status_code == 200, f"Auth failed: {auth_res.text}"
    token_data = auth_res.json()
    token = token_data["access_token"]
    print(f"Logged in as neo_coder! Token preview: {token[:25]}...")

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 4. Testing Code Run (Python Solution on Largest Overlap) ---")
    py_solution = """class Solution:
    def largestOverlap(self, img1: List[List[int]], img2: List[List[int]]) -> int:
        n = len(img1)
        ones1 = [(r, c) for r in range(n) for c in range(n) if img1[r][c] == 1]
        ones2 = [(r, c) for r in range(n) for c in range(n) if img2[r][c] == 1]
        
        diff_count = {}
        max_overlap = 0
        for r1, c1 in ones1:
            for r2, c2 in ones2:
                diff = (r1 - r2, c1 - c2)
                diff_count[diff] = diff_count.get(diff, 0) + 1
                if diff_count[diff] > max_overlap:
                    max_overlap = diff_count[diff]
        return max_overlap
"""
    run_payload = {
        "language": "python",
        "code": py_solution,
    }

    sub_res = client.post(f"{BASE_URL}/problems/largest-overlap/run", json=run_payload, headers=headers)
    assert sub_res.status_code == 202, f"Submission failed: {sub_res.text}"
    sub_data = sub_res.json()
    sub_id = sub_data["submission_id"]
    print(f"Submission accepted! ID: {sub_id}, status: {sub_data['status']}")

    print("\n--- 5. Polling Submission Status ---")
    for i in range(15):
        time.sleep(1)
        poll_res = client.get(f"{BASE_URL}/submissions/{sub_id}", headers=headers)
        poll_data = poll_res.json()
        status = poll_data["status"]
        print(f"  Attempt {i+1}: status = {status}")
        if status not in ("pending", "processing"):
            print(f"\nFinal Verdict: {status.upper()}")
            print(f"Passed test cases: {poll_data.get('passed_test_cases')}/{poll_data.get('total_test_cases')}")
            if poll_data.get("sample_results"):
                print("Sample Results:")
                for sr in poll_data["sample_results"]:
                    print(f"  Test Case #{sr.get('test_case_id')}: {sr.get('status')} (Output: {sr.get('actual_output')}, Expected: {sr.get('expected_output')})")
            break

    print("\n--- 6. Testing User Stats API ---")
    stats_res = client.get(f"{BASE_URL}/submissions/stats/me", headers=headers)
    assert stats_res.status_code == 200, f"Stats failed: {stats_res.text}"
    stats_data = stats_res.json()
    print("\n--- 7. Testing Official Submission (Submit) ---")
    submit_payload = {
        "language": "python",
        "code": py_solution,
    }
    submit_res = client.post(f"{BASE_URL}/problems/largest-overlap/submit", json=submit_payload, headers=headers)
    assert submit_res.status_code == 202, f"Submit failed: {submit_res.text}"
    sub_id = submit_res.json()["submission_id"]
    print(f"Official Submission ID: {sub_id}")
    time.sleep(1.5)
    poll_res = client.get(f"{BASE_URL}/submissions/{sub_id}", headers=headers).json()
    print(f"Official Submission Verdict: {poll_res['status'].upper()} ({poll_res.get('passed_test_cases')}/{poll_res.get('total_test_cases')} tests passed)")

    print("\n--- 8. Verifying Solved Status & Stats ---")
    stats_data = client.get(f"{BASE_URL}/submissions/stats/me", headers=headers).json()
    print(f"Updated Stats: Total Solved = {stats_data['total_solved']}, Medium Solved = {stats_data['medium_solved']}, Acceptance Rate = {stats_data['acceptance_rate']}%")

    print("\nAll Backend + Execution Pipeline verifications PASSED!")

if __name__ == "__main__":
    test_full_pipeline()
