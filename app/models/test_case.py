from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Text, Integer, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.problem import Problem


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="test_cases",
    )

    __table_args__ = (
        # Partial index for fast sample test cases retrieval
        Index("idx_test_cases_sample", "problem_id", postgresql_where=(is_sample.is_(True))),
        Index("idx_test_cases_problem_id", "problem_id"),
    )
