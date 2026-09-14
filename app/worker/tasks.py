"""Celery tasks and async submission evaluation pipeline."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import get_settings
from app.models.enums import ProblemSolveStatus, SubmissionKind, SubmissionStatus
from app.models.problem import Problem
from app.models.status import UserProblemStatus
from app.models.submission import Submission
from app.models.template import ProblemTemplate
from app.models.test_case import TestCase
from app.services.cache_service import CacheService
from app.services.harness_service import harness_service, OUTPUT_DELIMITER
from app.services.judge0_service import judge0_service
from app.services.s3_service import s3_service
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_scoped_session_factory():
    """Create a task-scoped engine with NullPool to avoid event-loop connection bleeding."""
    task_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        future=True,
    )
    session_factory = async_sessionmaker(
        bind=task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_factory, task_engine


async def _evaluate_submission_async(submission_id_str: str) -> Dict[str, Any]:
    """
    Core async evaluation logic:
    1. Fetch submission details from DB.
    2. Download testcases from S3.
    3. Execute sequentially against Judge0.
    4. Update submissions and user_problem_status tables.
    5. Cache result in Redis for high-speed client polling.
    """
    submission_id = uuid.UUID(submission_id_str)
    session_factory, task_engine = _get_scoped_session_factory()

    try:
        async with session_factory() as db:
            # 1. Fetch submission
            stmt = select(Submission).where(Submission.id == submission_id)
            result = await db.execute(stmt)
            submission = result.scalar_one_or_none()

            if not submission:
                logger.error("Submission %s not found for evaluation", submission_id_str)
                return {"error": "Submission not found"}

            # Set status to PROCESSING
            submission.status = SubmissionStatus.PROCESSING
            await db.commit()

            # Update Redis cache with processing status
            await CacheService.set_json(
                f"submissions:detail:{submission_id_str}",
                {
                    "id": str(submission.id),
                    "status": SubmissionStatus.PROCESSING.value,
                    "kind": submission.kind.value,
                },
                ttl=300,
            )

            # 2. Lookup problem to get slug
            prob_stmt = select(Problem).where(Problem.id == submission.problem_id)
            prob_res = await db.execute(prob_stmt)
            problem = prob_res.scalar_one_or_none()
            slug = problem.slug if problem else None

            # 3. Check for consolidated S3 bundle first
            bundle = await s3_service.get_problem_testcase_bundle_async(
                problem_id=submission.problem_id, slug=slug
            )

            resolved_inputs: List[str] = []
            resolved_outputs: List[str] = []
            testcase_meta: List[Dict[str, Any]] = []
            method_name: Optional[str] = None

            if bundle and "test_cases" in bundle and bundle["test_cases"]:
                method_name = bundle.get("method_name")
                raw_cases = bundle["test_cases"]
                if submission.kind == SubmissionKind.RUN:
                    sample_cases = [tc for tc in raw_cases if tc.get("is_sample", False)]
                    active_cases = sample_cases if sample_cases else raw_cases[:3]
                else:
                    active_cases = raw_cases

                for idx, tc in enumerate(active_cases):
                    inp = tc.get("input", "")
                    out = tc.get("expected_output") or tc.get("expected") or ""
                    resolved_inputs.append(str(inp))
                    resolved_outputs.append(str(out))
                    testcase_meta.append({
                        "id": tc.get("id", idx + 1),
                        "is_sample": tc.get("is_sample", False),
                    })
            else:
                # Fallback to database test cases
                tc_query = select(TestCase).where(TestCase.problem_id == submission.problem_id)
                if submission.kind == SubmissionKind.RUN:
                    tc_query = tc_query.where(TestCase.is_sample.is_(True))
                tc_query = tc_query.order_by(TestCase.id.asc())

                tc_result = await db.execute(tc_query)
                db_cases: List[TestCase] = list(tc_result.scalars().all())

                if not db_cases:
                    submission.status = SubmissionStatus.ACCEPTED
                    submission.runtime_ms = 10
                    submission.memory_kb = 12000
                    await db.commit()
                    return {"status": "accepted", "test_cases": 0}

                for tc in db_cases:
                    stdin = (
                        await s3_service.get_text_async(tc.input)
                        if tc.input.startswith("testcases/")
                        else tc.input
                    )
                    expected_out = (
                        await s3_service.get_text_async(tc.expected_output)
                        if tc.expected_output.startswith("testcases/")
                        else tc.expected_output
                    )
                    resolved_inputs.append(stdin)
                    resolved_outputs.append(expected_out)
                    testcase_meta.append({
                        "id": tc.id,
                        "is_sample": tc.is_sample,
                    })

            # 4. Retrieve problem template & stitch with harness
            tmpl_stmt = select(ProblemTemplate).where(
                ProblemTemplate.problem_id == submission.problem_id,
                ProblemTemplate.language == submission.language,
            )
            tmpl_res = await db.execute(tmpl_stmt)
            template = tmpl_res.scalar_one_or_none()
            driver_code = template.driver_code if template else None

            if not method_name and template and template.starter_code:
                import re
                py_m = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\(', template.starter_code)
                if py_m:
                    method_name = py_m.group(1)
                else:
                    fn_m = re.search(r'(?:var|let|const|function)\s+([a-zA-Z0-9_]+)', template.starter_code)
                    if fn_m:
                        method_name = fn_m.group(1)
                    else:
                        cpp_m = re.search(r'\w+\s+([a-zA-Z0-9_]+)\s*\(', template.starter_code)
                        if cpp_m:
                            method_name = cpp_m.group(1)

            executable_code = harness_service.assemble_code(
                language=submission.language,
                user_code=submission.code,
                custom_driver=driver_code,
                method_name=method_name,
            )

            batched_stdin = harness_service.batch_inputs(resolved_inputs)

            # 5. Execute via Judge0 in a SINGLE CALL (raw execution without diffing)
            exec_res = await judge0_service.execute_test_case(
                source_code=executable_code,
                language=submission.language,
                stdin=batched_stdin,
                expected_output=None,
            )

            tc_status = exec_res["status"]
            max_runtime_ms = exec_res.get("runtime_ms", 0)
            max_memory_kb = exec_res.get("memory_kb", 0)
            stdout = exec_res.get("stdout", "")
            stderr = exec_res.get("stderr", "")

            first_failed_case = None

            # Check fatal errors
            if tc_status in (
                SubmissionStatus.COMPILATION_ERROR,
                SubmissionStatus.TIME_LIMIT_EXCEEDED,
                SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
                SubmissionStatus.RUNTIME_ERROR,
                SubmissionStatus.INTERNAL_ERROR,
            ):
                final_status = tc_status
                error_message = stderr or exec_res.get("compile_output") or f"Execution failed: {tc_status.value}"
                passed_count = 0
                sample_results = [
                    {
                        "test_case_id": meta["id"],
                        "status": final_status.value,
                        "runtime_ms": max_runtime_ms,
                        "memory_kb": max_memory_kb,
                        "stdin": resolved_inputs[i] if meta["is_sample"] else None,
                        "expected_output": resolved_outputs[i] if meta["is_sample"] else None,
                        "actual_output": error_message if meta["is_sample"] else None,
                        "error_message": error_message,
                    }
                    for i, meta in enumerate(testcase_meta)
                ]
                if resolved_inputs:
                    first_failed_case = {
                        "test_case_number": 1,
                        "total_test_cases": len(resolved_inputs),
                        "input": harness_service.truncate_text(resolved_inputs[0]),
                        "expected_output": harness_service.truncate_text(resolved_outputs[0]) if resolved_outputs else "",
                        "actual_output": harness_service.truncate_text(error_message),
                    }
            else:
                # Parse batched outputs against each testcase
                parsed = harness_service.parse_outputs(stdout, resolved_outputs)
                passed_count = sum(1 for p in parsed if p["passed"])
                all_passed = (passed_count == len(resolved_inputs))

                # Check if any testcase ran into a runtime error (e.g. starts with "Error:")
                has_runtime_error = any(p["actual"].startswith("Error:") for p in parsed)

                if all_passed:
                    final_status = SubmissionStatus.ACCEPTED
                    error_message = None
                elif has_runtime_error:
                    final_status = SubmissionStatus.RUNTIME_ERROR
                    first_err = next((p["actual"] for p in parsed if p["actual"].startswith("Error:")), "Runtime error")
                    error_message = first_err
                else:
                    final_status = SubmissionStatus.WRONG_ANSWER
                    first_failed_case = harness_service.extract_first_failure(
                        parsed, resolved_inputs, resolved_outputs
                    )
                    error_message = (
                        f"Failed on test case {first_failed_case['test_case_number']}"
                        if first_failed_case
                        else "Output did not match expected"
                    )

                if not all_passed and not first_failed_case:
                    first_failed_case = harness_service.extract_first_failure(
                        parsed, resolved_inputs, resolved_outputs
                    )

                sample_results = [
                    {
                        "test_case_id": meta["id"],
                        "status": (
                            SubmissionStatus.ACCEPTED.value
                            if p["passed"]
                            else (
                                SubmissionStatus.RUNTIME_ERROR.value
                                if p["actual"].startswith("Error:")
                                else SubmissionStatus.WRONG_ANSWER.value
                            )
                        ),
                        "runtime_ms": max_runtime_ms,
                        "memory_kb": max_memory_kb,
                        "stdin": resolved_inputs[i] if meta["is_sample"] else None,
                        "expected_output": resolved_outputs[i] if meta["is_sample"] else None,
                        "actual_output": p["actual"] if meta["is_sample"] else None,
                        "error_message": None if p["passed"] else (p["actual"] if p["actual"].startswith("Error:") else "Output did not match expected"),
                    }
                    for i, (meta, p) in enumerate(zip(testcase_meta, parsed))
                ]

            # 6. Update Submission entity in PostgreSQL
            submission.status = final_status
            submission.runtime_ms = max_runtime_ms
            submission.memory_kb = max_memory_kb
            submission.error_message = error_message

            # 7. Update UserProblemStatus if official submit
            if submission.kind == SubmissionKind.SUBMIT:
                status_stmt = select(UserProblemStatus).where(
                    (UserProblemStatus.user_id == submission.user_id)
                    & (UserProblemStatus.problem_id == submission.problem_id)
                )
                status_res = await db.execute(status_stmt)
                ups = status_res.scalar_one_or_none()

                if ups is None:
                    new_status = (
                        ProblemSolveStatus.SOLVED
                        if final_status == SubmissionStatus.ACCEPTED
                        else ProblemSolveStatus.ATTEMPTED
                    )
                    ups = UserProblemStatus(
                        user_id=submission.user_id,
                        problem_id=submission.problem_id,
                        status=new_status,
                    )
                    db.add(ups)
                else:
                    if final_status == SubmissionStatus.ACCEPTED:
                        ups.status = ProblemSolveStatus.SOLVED

            await db.commit()

        # 8. Cache final detailed evaluation result in Redis
        cache_payload = {
            "id": str(submission.id),
            "user_id": str(submission.user_id),
            "problem_id": submission.problem_id,
            "language": submission.language,
            "kind": submission.kind.value,
            "status": submission.status.value,
            "runtime_ms": submission.runtime_ms,
            "memory_kb": submission.memory_kb,
            "error_message": submission.error_message,
            "passed_test_cases": passed_count,
            "total_test_cases": len(resolved_inputs),
            "sample_results": sample_results,
            "first_failed_case": first_failed_case,
            "created_at": submission.created_at.isoformat(),
            "updated_at": submission.updated_at.isoformat(),
        }

        await CacheService.set_json(
            f"submissions:detail:{submission_id_str}",
            cache_payload,
            ttl=3600,
        )

        return cache_payload
    finally:
        await task_engine.dispose()


@celery_app.task(name="app.worker.tasks.evaluate_submission_task")
def evaluate_submission_task(submission_id_str: str) -> Dict[str, Any]:
    """Synchronous Celery task wrapper invoking the async evaluation pipeline."""
    return asyncio.run(_evaluate_submission_async(submission_id_str))
