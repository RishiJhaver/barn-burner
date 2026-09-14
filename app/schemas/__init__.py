"""Pydantic schemas and DTOs for request/response validation."""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserSyncRequest,
    UserResponse,
)
from app.schemas.tag import (
    TagBase,
    TagCreate,
    TagResponse,
)
from app.schemas.template import (
    ProblemTemplateBase,
    ProblemTemplateCreate,
    ProblemTemplateUpdate,
    ProblemTemplateResponse,
)
from app.schemas.test_case import (
    TestCaseBase,
    TestCaseCreate,
    TestCaseResponse,
    SampleTestCaseResponse,
)
from app.schemas.problem import (
    ProblemBase,
    ProblemCreate,
    ProblemUpdate,
    ProblemListItemResponse,
    ProblemDetailResponse,
    ProblemListQuery,
)
from app.schemas.submission import (
    SubmissionRunRequest,
    SubmissionSubmitRequest,
    SubmissionResponse,
    SubmissionDetailResponse,
    SubmissionListQuery,
)
from app.schemas.status import (
    UserProblemStatusResponse,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserSyncRequest",
    "UserResponse",
    "TagBase",
    "TagCreate",
    "TagResponse",
    "ProblemTemplateBase",
    "ProblemTemplateCreate",
    "ProblemTemplateUpdate",
    "ProblemTemplateResponse",
    "TestCaseBase",
    "TestCaseCreate",
    "TestCaseResponse",
    "SampleTestCaseResponse",
    "ProblemBase",
    "ProblemCreate",
    "ProblemUpdate",
    "ProblemListItemResponse",
    "ProblemDetailResponse",
    "ProblemListQuery",
    "SubmissionRunRequest",
    "SubmissionSubmitRequest",
    "SubmissionResponse",
    "SubmissionDetailResponse",
    "SubmissionListQuery",
    "UserProblemStatusResponse",
]
