from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.problem import Problem


class ProblemTemplate(Base, TimestampMixin):
    __tablename__ = "problem_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    driver_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="templates",
    )

    __table_args__ = (
        UniqueConstraint("problem_id", "language", name="uq_problem_language"),
        Index("idx_problem_templates_problem_id", "problem_id"),
    )
