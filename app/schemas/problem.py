from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ProblemDifficulty
from app.schemas.tag import TagResponse
from app.schemas.template import ProblemTemplateResponse, ProblemTemplateCreate
from app.schemas.test_case import SampleTestCaseResponse, TestCaseCreate


class ProblemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=128)
    description: str
    difficulty: ProblemDifficulty


class ProblemCreate(ProblemBase):
    published: bool = False
    tag_ids: List[int] = Field(default_factory=list)
    templates: List[ProblemTemplateCreate] = Field(default_factory=list)
    test_cases: List[TestCaseCreate] = Field(default_factory=list)


class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty: Optional[ProblemDifficulty] = None
    published: Optional[bool] = None
    tag_ids: Optional[List[int]] = None


class ProblemListItemResponse(BaseModel):
    id: int
    slug: str
    title: str
    difficulty: ProblemDifficulty
    published: bool
    created_at: datetime
    tags: List[TagResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProblemDetailResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    difficulty: ProblemDifficulty
    published: bool
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = Field(default_factory=list)
    templates: List[ProblemTemplateResponse] = Field(default_factory=list)
    sample_test_cases: List[SampleTestCaseResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProblemListQuery(BaseModel):
    last_id: Optional[int] = Field(None, description="Keyset pagination: id of the last problem seen")
    limit: int = Field(20, ge=1, le=100, description="Number of problems to fetch")
    difficulty: Optional[ProblemDifficulty] = None
    tag: Optional[str] = None
