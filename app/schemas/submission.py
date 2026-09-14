"""Pydantic schemas and validation for code execution, runs, and submissions."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import SubmissionKind, SubmissionStatus


class SupportedLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    CPP = "cpp"
    JAVA = "java"
    GO = "go"
    RUST = "rust"


class RunCodeRequest(BaseModel):
    """Payload to test code against sample test cases (non-blocking)."""
    language: SupportedLanguage
    code: str = Field(..., min_length=1, max_length=65536, description="Source code up to 64KB")
    custom_input: Optional[str] = Field(None, max_length=10000, description="Optional custom test input")


class SubmitCodeRequest(BaseModel):
    """Payload to officially submit code against hidden test suite (non-blocking)."""
    language: SupportedLanguage
    code: str = Field(..., min_length=1, max_length=65536, description="Source code up to 64KB")


class SubmissionAcceptedResponse(BaseModel):
    """Immediate HTTP 202 Accepted response returned without blocking the user."""
    submission_id: Optional[uuid.UUID] = None
    id: Optional[uuid.UUID] = None
    status: SubmissionStatus
    kind: SubmissionKind
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context) -> None:
        if self.submission_id is None and self.id is not None:
            self.submission_id = self.id
        elif self.id is None and self.submission_id is not None:
            self.id = self.submission_id


class TestCaseExecutionResult(BaseModel):
    """Detailed result per test case."""
    test_case_id: Optional[int] = None
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error_message: Optional[str] = None


class SubmissionDetailResponse(BaseModel):
    """Comprehensive submission evaluation verdict and metrics."""
    id: uuid.UUID
    user_id: uuid.UUID
    problem_id: int
    problem_slug: Optional[str] = None
    problem_title: Optional[str] = None
    language: str
    kind: SubmissionKind
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    error_message: Optional[str] = None
    passed_test_cases: Optional[int] = None
    total_test_cases: Optional[int] = None
    sample_results: Optional[List[TestCaseExecutionResult]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionListItemResponse(BaseModel):
    """Summary item for paginated submissions history."""
    id: uuid.UUID
    problem_id: int
    problem_title: Optional[str] = None
    problem_slug: Optional[str] = None
    language: str
    kind: SubmissionKind
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """Paginated response for user submissions history."""
    total: int
    limit: int
    offset: int
    items: List[SubmissionListItemResponse]

    model_config = ConfigDict(from_attributes=True)


class UserSubmissionStats(BaseModel):
    """Overall coding progress and submission statistics."""
    total_submissions: int
    accepted_submissions: int
    acceptance_rate: float
    easy_solved: int
    medium_solved: int
    hard_solved: int
    total_solved: int

    model_config = ConfigDict(from_attributes=True)


# Aliases for backwards compatibility
SubmissionRunRequest = RunCodeRequest
SubmissionSubmitRequest = SubmitCodeRequest
SubmissionResponse = SubmissionAcceptedResponse
SubmissionListQuery = BaseModel


