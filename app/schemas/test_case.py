from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TestCaseBase(BaseModel):
    __test__ = False

    input: str
    expected_output: str
    is_sample: bool = False


class TestCaseCreate(TestCaseBase):
    pass


class SampleTestCaseResponse(BaseModel):
    id: int
    input: str
    expected_output: str

    model_config = ConfigDict(from_attributes=True)


class TestCaseResponse(TestCaseBase):
    id: int
    problem_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
