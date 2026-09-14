"""Problems management and querying endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.config import get_settings
from app.models.enums import ProblemDifficulty
from app.models.problem import Problem
from app.models.tag import Tag
from app.models.template import ProblemTemplate
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.problem import (
    ProblemCreate,
    ProblemDetailResponse,
    ProblemListItemResponse,
    ProblemUpdate,
)
from app.schemas.tag import TagResponse
from app.schemas.template import ProblemTemplateResponse
from app.schemas.test_case import SampleTestCaseResponse
from app.services.cache_service import CacheService
from app.services.s3_service import s3_service

router = APIRouter()
settings = get_settings()


async def _build_problem_detail_response(
    problem: Problem, db: AsyncSession
) -> ProblemDetailResponse:
    """Helper to assemble ProblemDetailResponse with resolved sample test case payloads."""
    # Query sample test cases
    tc_query = (
        select(TestCase)
        .where((TestCase.problem_id == problem.id) & (TestCase.is_sample.is_(True)))
        .order_by(TestCase.id.asc())
    )
    tc_result = await db.execute(tc_query)
    sample_tcs = tc_result.scalars().all()

    resolved_samples: List[SampleTestCaseResponse] = []
    for tc in sample_tcs:
        # Resolve text from S3 if key format used
        input_text = s3_service.get_text(tc.input) if tc.input.startswith("testcases/") else tc.input
        output_text = (
            s3_service.get_text(tc.expected_output)
            if tc.expected_output.startswith("testcases/")
            else tc.expected_output
        )
        resolved_samples.append(
            SampleTestCaseResponse(
                id=tc.id,
                input=input_text,
                expected_output=output_text,
            )
        )

    return ProblemDetailResponse(
        id=problem.id,
        slug=problem.slug,
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        published=problem.published,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        tags=[TagResponse.model_validate(t) for t in problem.tags],
        templates=[ProblemTemplateResponse.model_validate(tmpl) for tmpl in problem.templates],
        sample_test_cases=resolved_samples,
    )


@router.get("", response_model=List[ProblemListItemResponse])
async def list_problems(
    last_id: Optional[int] = Query(None, description="Keyset pagination cursor (last problem ID seen)"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    difficulty: Optional[ProblemDifficulty] = Query(None, description="Filter by difficulty"),
    tag: Optional[str] = Query(None, description="Filter by tag name or slug"),
    db: AsyncSession = Depends(get_db),
) -> List[ProblemListItemResponse]:
    """
    List published problems using keyset pagination on (created_at DESC, id DESC).
    Results are cached in Redis.
    """
    cache_key = CacheService.problem_list_key(
        last_id=last_id,
        limit=limit,
        difficulty=difficulty.value if difficulty else None,
        tag=tag,
    )

    cached_data = await CacheService.get_json(cache_key)
    if cached_data is not None:
        return [ProblemListItemResponse.model_validate(item) for item in cached_data]

    # Build DB Query matching idx_problems_published_created index
    query = (
        select(Problem)
        .options(selectinload(Problem.tags))
        .where(Problem.published.is_(True))
    )

    if difficulty:
        query = query.where(Problem.difficulty == difficulty)

    if tag:
        query = query.join(Problem.tags).where((Tag.slug == tag) | (Tag.name == tag))

    if last_id:
        subq = select(Problem.created_at).where(Problem.id == last_id).scalar_subquery()
        query = query.where(
            (Problem.created_at < subq) | ((Problem.created_at == subq) & (Problem.id < last_id))
        )

    query = query.order_by(Problem.created_at.desc(), Problem.id.desc()).limit(limit)

    result = await db.execute(query)
    problems = result.scalars().all()

    response_items = [ProblemListItemResponse.model_validate(p) for p in problems]

    # Cache the serialized result in Redis
    await CacheService.set_json(
        cache_key,
        [item.model_dump(mode="json") for item in response_items],
        ttl=settings.CACHE_PROBLEMS_LIST_TTL,
    )

    return response_items


@router.get("/{slug}", response_model=ProblemDetailResponse)
async def get_problem_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ProblemDetailResponse:
    """
    Retrieve problem details by slug, including code templates and sample test cases.
    Results are cached in Redis.
    """
    cache_key = CacheService.problem_detail_key(slug)
    cached_data = await CacheService.get_json(cache_key)
    if cached_data is not None:
        return ProblemDetailResponse.model_validate(cached_data)

    query = (
        select(Problem)
        .options(selectinload(Problem.tags), selectinload(Problem.templates))
        .where(Problem.slug == slug)
    )
    result = await db.execute(query)
    problem = result.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with slug '{slug}' not found",
        )

    response = await _build_problem_detail_response(problem, db)

    # Cache in Redis
    await CacheService.set_json(
        cache_key,
        response.model_dump(mode="json"),
        ttl=settings.CACHE_PROBLEM_DETAIL_TTL,
    )

    return response


@router.post("", response_model=ProblemDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_in: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ProblemDetailResponse:
    """
    Create a new problem with starter code templates, tags, and S3-stored test cases.
    Admin only.
    """
    # Check duplicate slug
    existing = await db.execute(select(Problem).where(Problem.slug == problem_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Problem with slug '{problem_in.slug}' already exists",
        )

    # Fetch associated tags
    tags: List[Tag] = []
    if problem_in.tag_ids:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(problem_in.tag_ids)))
        tags = list(tag_result.scalars().all())

    # Create Problem entity
    problem = Problem(
        title=problem_in.title,
        slug=problem_in.slug,
        description=problem_in.description,
        difficulty=problem_in.difficulty,
        published=problem_in.published,
        tags=tags,
    )
    db.add(problem)
    await db.flush()  # Generates problem.id for foreign keys

    # Add starter code templates
    for tmpl in problem_in.templates:
        template_obj = ProblemTemplate(
            problem_id=problem.id,
            language=tmpl.language,
            starter_code=tmpl.starter_code,
            driver_code=tmpl.driver_code,
        )
        db.add(template_obj)

    # Upload test cases to S3 and save metadata in DB
    for idx, tc in enumerate(problem_in.test_cases, start=1):
        input_key, output_key = s3_service.upload_testcase(
            problem_id=problem.id,
            tc_identifier=str(idx),
            input_data=tc.input,
            expected_output=tc.expected_output,
        )
        test_case_obj = TestCase(
            problem_id=problem.id,
            input=input_key,
            expected_output=output_key,
            is_sample=tc.is_sample,
        )
        db.add(test_case_obj)

    await db.commit()

    # Re-query with eager loads
    query = (
        select(Problem)
        .options(selectinload(Problem.tags), selectinload(Problem.templates))
        .where(Problem.id == problem.id)
    )
    result = await db.execute(query)
    created_problem = result.scalar_one()

    # Invalidate Redis list cache
    await CacheService.invalidate_problem_cache(created_problem.slug)

    return await _build_problem_detail_response(created_problem, db)


@router.patch("/{problem_id}", response_model=ProblemDetailResponse)
async def update_problem(
    problem_id: int,
    problem_update: ProblemUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ProblemDetailResponse:
    """
    Update problem metadata, difficulty, publication status, or tags.
    Admin only.
    """
    query = (
        select(Problem)
        .options(selectinload(Problem.tags), selectinload(Problem.templates))
        .where(Problem.id == problem_id)
    )
    result = await db.execute(query)
    problem = result.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {problem_id} not found",
        )

    # Update basic fields if provided
    if problem_update.title is not None:
        problem.title = problem_update.title
    if problem_update.description is not None:
        problem.description = problem_update.description
    if problem_update.difficulty is not None:
        problem.difficulty = problem_update.difficulty
    if problem_update.published is not None:
        problem.published = problem_update.published

    # Update tags if provided
    if problem_update.tag_ids is not None:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(problem_update.tag_ids)))
        problem.tags = list(tag_result.scalars().all())

    await db.commit()
    await db.refresh(problem)

    # Invalidate Redis cache for this problem and problem lists
    await CacheService.invalidate_problem_cache(problem.slug)

    return await _build_problem_detail_response(problem, db)
