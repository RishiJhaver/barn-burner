from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, ForeignKey, Column, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.problem import Problem

# Junction table for Problem <-> Tag many-to-many relationship
problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", Integer, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    problems: Mapped[List["Problem"]] = relationship(
        "Problem",
        secondary=problem_tags,
        back_populates="tags",
    )
