import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import SubmissionKind, SubmissionStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    # UUID PK to prevent ID enumeration across users
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[SubmissionKind] = mapped_column(
        Enum(
            SubmissionKind,
            name="submission_kind",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubmissionKind.SUBMIT,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            name="submission_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubmissionStatus.PENDING,
    )
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    judge0_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="submissions",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="submissions",
    )

    __table_args__ = (
        # Partial index for submission history (only 'submit' entries, excluding 'run')
        Index(
            "idx_submissions_user_history",
            "user_id",
            "created_at",
            postgresql_where=(kind == SubmissionKind.SUBMIT),
        ),
        Index("idx_submissions_user_problem", "user_id", "problem_id", "created_at"),
        Index(
            "idx_submissions_judge0_token",
            "judge0_token",
            postgresql_where=(judge0_token.is_not(None)),
        ),
    )
