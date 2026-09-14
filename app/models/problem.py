from typing import TYPE_CHECKING, List
from sqlalchemy import String, Text, Boolean, Integer, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import ProblemDifficulty
from app.models.tag import problem_tags

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.template import ProblemTemplate
    from app.models.test_case import TestCase
    from app.models.submission import Submission
    from app.models.status import UserProblemStatus


class Problem(Base, TimestampMixin):
    __tablename__ = "problems"

    # Serial integer PK for compact FKs and efficient indexing
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[ProblemDifficulty] = mapped_column(
        Enum(
            ProblemDifficulty,
            name="problem_difficulty",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=problem_tags,
        back_populates="problems",
        lazy="selectin",
    )
    templates: Mapped[List["ProblemTemplate"]] = relationship(
        "ProblemTemplate",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    user_statuses: Mapped[List["UserProblemStatus"]] = relationship(
        "UserProblemStatus",
        back_populates="problem",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Keyset pagination index for published problems ordered by created_at DESC, id DESC
        Index("idx_problems_published_created", "published", "created_at", "id"),
    )
