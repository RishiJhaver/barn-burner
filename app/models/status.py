import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Enum, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.enums import ProblemSolveStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem


class UserProblemStatus(Base):
    __tablename__ = "user_problem_status"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    problem_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[ProblemSolveStatus] = mapped_column(
        Enum(
            ProblemSolveStatus,
            name="problem_solve_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ProblemSolveStatus.ATTEMPTED,
    )
    last_submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="problem_statuses",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="user_statuses",
    )

    __table_args__ = (
        Index("idx_user_problem_status_user_id", "user_id"),
    )
