from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProblemTemplateBase(BaseModel):
    language: str = Field(..., min_length=1, max_length=32)
    starter_code: str
    driver_code: Optional[str] = None


class ProblemTemplateCreate(ProblemTemplateBase):
    pass


class ProblemTemplateUpdate(BaseModel):
    starter_code: Optional[str] = None
    driver_code: Optional[str] = None


class ProblemTemplateResponse(ProblemTemplateBase):
    id: int
    problem_id: int
    driver_code: Optional[str] = Field(default=None, exclude=True)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
