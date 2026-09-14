"""Code execution, run, and submission API endpoints with non-blocking 202 responses."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.rate_limiter import RateLimiter
from app.models.enums import ProblemDifficulty, ProblemSolveStatus, SubmissionKind, SubmissionStatus, UserRole
from app.models.problem import Problem
from app.models.status import UserProblemStatus
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import (
    RunCodeRequest,
    SubmitCodeRequest,
    SubmissionAcceptedResponse,
    SubmissionDetailResponse,
    SubmissionListItemResponse,
    UserSubmissionStats,
)
from app.services.cache_service import CacheService
from app.worker.tasks import _evaluate_submission_async, evaluate_submission_task

router = APIRouter()
execution_rate_limiter = RateLimiter(action="code_execution")


def _dispatch_task(submission_id: uuid.UUID, background_tasks: BackgroundTasks) -> None:
    """
    Dispatch non-blocking execution task via FastAPI BackgroundTasks (guaranteeing execution
    both in automated tests and standalone environments), and publish to Celery for distributed workers.
    """
    sub_id_str = str(submission_id)
    background_tasks.add_task(_evaluate_submission_async, sub_id_str)
    try:
        evaluate_submission_task.delay(sub_id_str)
    except Exception:
        pass


@router.post(
    "/problems/{slug}/run",
    response_model=SubmissionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_code(
    slug: str,
    request: RunCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(execution_rate_limiter),
) -> SubmissionAcceptedResponse:
    """
    Execute code against sample test cases (non-blocking).
    Protected by short-window anti-spam rate limiter.
    Immediately returns HTTP 202 with submission_id for polling.
    """
    # 1. Look up problem
    stmt = select(Problem).where(Problem.slug == slug)
    res = await db.execute(stmt)
    problem = res.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{slug}' not found",
        )

    # 2. Create Submission entity (status: pending)
    submission = Submission(
        id=uuid.uuid4(),
        user_id=current_user.id,
        problem_id=problem.id,
        language=request.language.value,
        code=request.code,
        kind=SubmissionKind.RUN,
        status=SubmissionStatus.PENDING,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 3. Dispatch non-blocking background evaluation
    _dispatch_task(submission.id, background_tasks)

    return SubmissionAcceptedResponse(
        submission_id=submission.id,
        status=submission.status,
        kind=submission.kind,
        created_at=submission.created_at,
    )


@router.post(
    "/problems/{slug}/submit",
    response_model=SubmissionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_code(
    slug: str,
    request: SubmitCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(execution_rate_limiter),
) -> SubmissionAcceptedResponse:
    """
    Officially submit code against full hidden test cases (non-blocking).
    Protected by short-window anti-spam rate limiter.
    Immediately returns HTTP 202 with submission_id for polling.
    """
    # 1. Look up problem
    stmt = select(Problem).where(Problem.slug == slug)
    res = await db.execute(stmt)
    problem = res.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{slug}' not found",
        )

    # 2. Create Submission entity
    submission = Submission(
        id=uuid.uuid4(),
        user_id=current_user.id,
        problem_id=problem.id,
        language=request.language.value,
        code=request.code,
        kind=SubmissionKind.SUBMIT,
        status=SubmissionStatus.PENDING,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 3. Dispatch non-blocking background evaluation
    _dispatch_task(submission.id, background_tasks)

    return SubmissionAcceptedResponse(
        submission_id=submission.id,
        status=submission.status,
        kind=submission.kind,
        created_at=submission.created_at,
    )


@router.get(
    "/submissions/stats",
    response_model=UserSubmissionStats,
    summary="Get User Coding & Submission Statistics",
)
async def get_user_submission_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSubmissionStats:
    """
    Aggregate overall coding stats for the authenticated user:
    - Total submissions & acceptance rate
    - Problems solved broken down by difficulty (Easy, Medium, Hard)
    """
    # 1. Submissions count & accepted count
    total_sub_stmt = select(func.count(Submission.id)).where(Submission.user_id == current_user.id)
    accepted_sub_stmt = select(func.count(Submission.id)).where(
        Submission.user_id == current_user.id,
        Submission.status == SubmissionStatus.ACCEPTED,
    )
    total_submissions = (await db.execute(total_sub_stmt)).scalar() or 0
    accepted_submissions = (await db.execute(accepted_sub_stmt)).scalar() or 0

    acceptance_rate = (
        round((accepted_submissions / total_submissions) * 100, 2)
        if total_submissions > 0
        else 0.0
    )

    # 2. Solved problems by difficulty from user_problem_status
    solved_diff_stmt = (
        select(Problem.difficulty, func.count(UserProblemStatus.problem_id))
        .join(Problem, UserProblemStatus.problem_id == Problem.id)
        .where(
            UserProblemStatus.user_id == current_user.id,
            UserProblemStatus.status == ProblemSolveStatus.SOLVED,
        )
        .group_by(Problem.difficulty)
    )
    diff_results = (await db.execute(solved_diff_stmt)).all()
    diff_counts = {row[0]: row[1] for row in diff_results}

    easy_solved = diff_counts.get(ProblemDifficulty.EASY, 0)
    medium_solved = diff_counts.get(ProblemDifficulty.MEDIUM, 0)
    hard_solved = diff_counts.get(ProblemDifficulty.HARD, 0)
    total_solved = easy_solved + medium_solved + hard_solved

    return UserSubmissionStats(
        total_submissions=total_submissions,
        accepted_submissions=accepted_submissions,
        acceptance_rate=acceptance_rate,
        easy_solved=easy_solved,
        medium_solved=medium_solved,
        hard_solved=hard_solved,
        total_solved=total_solved,
    )


@router.get(
    "/submissions",
    response_model=List[SubmissionListItemResponse],
)
async def list_my_submissions(
    response: Response,
    problem_slug: Optional[str] = Query(None, description="Filter by problem slug"),
    problem_id: Optional[int] = Query(None, description="Filter by problem ID"),
    status: Optional[SubmissionStatus] = Query(None, description="Filter by submission status"),
    language: Optional[str] = Query(None, description="Filter by language"),
    kind: Optional[SubmissionKind] = Query(None, description="Filter by kind (run vs submit)"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SubmissionListItemResponse]:
    """
    Retrieve submission history for the authenticated user with advanced filters and pagination.
    Sets X-Total-Count response header with total matches.
    """
    base_query = (
        select(Submission)
        .options(selectinload(Submission.problem))
        .join(Problem, Submission.problem_id == Problem.id)
        .where(Submission.user_id == current_user.id)
    )
    count_query = (
        select(func.count(Submission.id))
        .select_from(Submission)
        .join(Problem, Submission.problem_id == Problem.id)
        .where(Submission.user_id == current_user.id)
    )

    if problem_slug:
        base_query = base_query.where(Problem.slug == problem_slug)
        count_query = count_query.where(Problem.slug == problem_slug)
    if problem_id:
        base_query = base_query.where(Submission.problem_id == problem_id)
        count_query = count_query.where(Submission.problem_id == problem_id)
    if status:
        base_query = base_query.where(Submission.status == status)
        count_query = count_query.where(Submission.status == status)
    if language:
        base_query = base_query.where(Submission.language == language)
        count_query = count_query.where(Submission.language == language)
    if kind:
        base_query = base_query.where(Submission.kind == kind)
        count_query = count_query.where(Submission.kind == kind)

    # Execute total count
    total_count = (await db.execute(count_query)).scalar() or 0
    response.headers["X-Total-Count"] = str(total_count)

    # Apply pagination and order
    query = base_query.order_by(Submission.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    submissions = res.scalars().all()

    return [
        SubmissionListItemResponse(
            id=s.id,
            problem_id=s.problem_id,
            problem_title=s.problem.title if s.problem else None,
            problem_slug=s.problem.slug if s.problem else None,
            language=s.language,
            kind=s.kind,
            status=s.status,
            runtime_ms=s.runtime_ms,
            memory_kb=s.memory_kb,
            created_at=s.created_at,
        )
        for s in submissions
    ]


@router.get(
    "/submissions/stats",
    response_model=UserSubmissionStats,
)
@router.get(
    "/submissions/stats/me",
    response_model=UserSubmissionStats,
)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSubmissionStats:
    """
    Retrieve user coding telemetry: total submissions, accepted count, acceptance rate,
    and solved counts broken down by difficulty (Easy, Medium, Hard).
    """
    # 1. Total & accepted submissions
    total_sub_stmt = select(func.count(Submission.id)).where(Submission.user_id == current_user.id)
    accepted_sub_stmt = select(func.count(Submission.id)).where(
        (Submission.user_id == current_user.id) & (Submission.status == SubmissionStatus.ACCEPTED)
    )
    total_res = await db.execute(total_sub_stmt)
    accepted_res = await db.execute(accepted_sub_stmt)
    total_subs = total_res.scalar() or 0
    accepted_subs = accepted_res.scalar() or 0
    acceptance_rate = round((accepted_subs / total_subs * 100.0), 2) if total_subs > 0 else 0.0

    # 2. Solved by difficulty
    solved_stmt = (
        select(Problem.difficulty, func.count(UserProblemStatus.problem_id))
        .join(Problem, UserProblemStatus.problem_id == Problem.id)
        .where(
            (UserProblemStatus.user_id == current_user.id)
            & (UserProblemStatus.status == ProblemSolveStatus.SOLVED)
        )
        .group_by(Problem.difficulty)
    )
    solved_res = await db.execute(solved_stmt)
    solved_rows = solved_res.all()

    difficulty_map = {row[0]: row[1] for row in solved_rows}
    easy_count = difficulty_map.get(ProblemDifficulty.EASY, 0)
    medium_count = difficulty_map.get(ProblemDifficulty.MEDIUM, 0)
    hard_count = difficulty_map.get(ProblemDifficulty.HARD, 0)
    total_solved = easy_count + medium_count + hard_count

    return UserSubmissionStats(
        total_submissions=total_subs,
        accepted_submissions=accepted_subs,
        acceptance_rate=acceptance_rate,
        easy_solved=easy_count,
        medium_solved=medium_count,
        hard_solved=hard_count,
        total_solved=total_solved,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetailResponse,
)
async def get_submission(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionDetailResponse:
    """
    Poll submission status, evaluation metrics, and verdicts.
    High-speed Redis cache supported.
    """
    sub_id_str = str(submission_id)

    # Check cache
    cached = await CacheService.get_json(f"submissions:detail:{sub_id_str}")
    if cached and (
        cached.get("user_id") == str(current_user.id)
        or current_user.role == UserRole.ADMIN
    ):
        return SubmissionDetailResponse.model_validate(cached)

    # Query DB with Problem relationship
    stmt = (
        select(Submission)
        .options(selectinload(Submission.problem))
        .where(Submission.id == submission_id)
    )
    res = await db.execute(stmt)
    submission = res.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    # Authorization guard: Users can only see their own submissions
    if submission.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this submission",
        )

    return SubmissionDetailResponse(
        id=submission.id,
        user_id=submission.user_id,
        problem_id=submission.problem_id,
        problem_slug=submission.problem.slug if submission.problem else None,
        problem_title=submission.problem.title if submission.problem else None,
        language=submission.language,
        kind=submission.kind,
        status=submission.status,
        runtime_ms=submission.runtime_ms,
        memory_kb=submission.memory_kb,
        error_message=submission.error_message,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )
