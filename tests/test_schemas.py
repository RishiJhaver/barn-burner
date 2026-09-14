"""Unit tests for Pydantic models and serialization."""

import uuid
from datetime import datetime, timezone
from app.models.enums import UserRole, ProblemDifficulty, SubmissionKind, SubmissionStatus
from app.schemas.user import UserCreate, UserResponse
from app.schemas.problem import ProblemCreate, ProblemDetailResponse, ProblemListItemResponse
from app.schemas.submission import SubmissionRunRequest, SubmissionResponse, SubmissionDetailResponse


def test_user_pydantic_schema():
    user_in = UserCreate(
        email="test@example.com",
        username="testuser",
        cognito_sub="cognito-12345",
        role=UserRole.USER,
    )
    assert user_in.email == "test@example.com"
    assert user_in.username == "testuser"
    assert user_in.role == UserRole.USER

    now = datetime.now(timezone.utc)
    user_out = UserResponse(
        id=uuid.uuid4(),
        cognito_sub="cognito-12345",
        email="test@example.com",
        username="testuser",
        role=UserRole.USER,
        created_at=now,
        updated_at=now,
    )
    assert user_out.username == "testuser"


def test_problem_pydantic_schema():
    problem_in = ProblemCreate(
        title="Two Sum",
        slug="two-sum",
        description="Given an array of integers...",
        difficulty=ProblemDifficulty.EASY,
        published=True,
    )
    assert problem_in.slug == "two-sum"
    assert problem_in.difficulty == ProblemDifficulty.EASY


def test_submission_pydantic_schema():
    sub_req = SubmissionRunRequest(
        language="python",
        code="def twoSum(): pass",
    )
    assert sub_req.language == "python"

    sub_res = SubmissionResponse(
        id=uuid.uuid4(),
        kind=SubmissionKind.RUN,
        status=SubmissionStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    assert sub_res.kind == SubmissionKind.RUN
    assert sub_res.status == SubmissionStatus.PENDING
