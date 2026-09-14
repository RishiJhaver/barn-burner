import uuid
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.status import UserProblemStatus


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # UUID primary key to avoid enumeration attacks and match external auth sub
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cognito_sub: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=UserRole.USER,
    )

    # Relationships
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    problem_statuses: Mapped[List["UserProblemStatus"]] = relationship(
        "UserProblemStatus",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_users_cognito_sub", "cognito_sub"),
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )
