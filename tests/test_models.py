"""Unit tests verifying SQLAlchemy models definitions and table constraints."""

from app.models.base import Base
from app.models import (
    User,
    Problem,
    Tag,
    ProblemTemplate,
    TestCase,
    Submission,
    UserProblemStatus,
)


def test_models_metadata():
    expected_tables = {
        "users",
        "problems",
        "tags",
        "problem_tags",
        "problem_templates",
        "test_cases",
        "submissions",
        "user_problem_status",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables: {expected_tables - registered_tables}"
    )


def test_problems_table_structure():
    table = Base.metadata.tables["problems"]
    columns = {c.name for c in table.columns}
    assert {"id", "slug", "title", "description", "difficulty", "published", "created_at", "updated_at"}.issubset(columns)

    index_names = {idx.name for idx in table.indexes}
    assert "idx_problems_published_created" in index_names


def test_submissions_table_structure():
    table = Base.metadata.tables["submissions"]
    columns = {c.name for c in table.columns}
    assert {"id", "user_id", "problem_id", "language", "code", "kind", "status", "runtime_ms", "memory_kb"}.issubset(columns)

    index_names = {idx.name for idx in table.indexes}
    assert "idx_submissions_user_history" in index_names


def test_test_cases_table_structure():
    table = Base.metadata.tables["test_cases"]
    columns = {c.name for c in table.columns}
    assert {"id", "problem_id", "input", "expected_output", "is_sample"}.issubset(columns)

    index_names = {idx.name for idx in table.indexes}
    assert "idx_test_cases_sample" in index_names
