from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import ProblemSolveStatus


class UserProblemStatusResponse(BaseModel):
    user_id: UUID
    problem_id: int
    status: ProblemSolveStatus
    last_submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)
