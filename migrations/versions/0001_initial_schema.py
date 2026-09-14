"""Initial schema migration

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-10 23:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('cognito_sub', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('role', sa.Enum('user', 'admin', name='user_role'), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cognito_sub'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_cognito_sub', 'users', ['cognito_sub'], unique=False)
    op.create_index('idx_users_email', 'users', ['email'], unique=False)

    # 2. problems table
    op.create_table(
        'problems',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='problem_difficulty'), nullable=False),
        sa.Column('published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_problems_published_created', 'problems', ['published', 'created_at', 'id'], unique=False)
    op.create_index('idx_problems_slug', 'problems', ['slug'], unique=False)

    # 3. tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )

    # 4. problem_tags junction table
    op.create_table(
        'problem_tags',
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('problem_id', 'tag_id')
    )
    op.create_index('idx_problem_tags_tag_id', 'problem_tags', ['tag_id'], unique=False)

    # 5. problem_templates table
    op.create_table(
        'problem_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=False),
        sa.Column('starter_code', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('problem_id', 'language', name='uq_problem_language')
    )
    op.create_index('idx_problem_templates_problem_id', 'problem_templates', ['problem_id'], unique=False)

    # 6. test_cases table
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=False),
        sa.Column('is_sample', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_test_cases_sample', 'test_cases', ['problem_id'], unique=False, postgresql_where=sa.text('is_sample = true'))
    op.create_index('idx_test_cases_problem_id', 'test_cases', ['problem_id'], unique=False)

    # 7. submissions table
    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('kind', sa.Enum('run', 'submit', name='submission_kind'), server_default='submit', nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'accepted', 'wrong_answer', 'time_limit_exceeded', 'memory_limit_exceeded', 'runtime_error', 'compilation_error', 'internal_error', name='submission_status'), server_default='pending', nullable=False),
        sa.Column('runtime_ms', sa.Integer(), nullable=True),
        sa.Column('memory_kb', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('judge0_token', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_submissions_user_history', 'submissions', ['user_id', 'created_at'], unique=False, postgresql_where=sa.text("kind = 'submit'"))
    op.create_index('idx_submissions_user_problem', 'submissions', ['user_id', 'problem_id', 'created_at'], unique=False)
    op.create_index('idx_submissions_judge0_token', 'submissions', ['judge0_token'], unique=False, postgresql_where=sa.text('judge0_token IS NOT NULL'))

    # 8. user_problem_status table
    op.create_table(
        'user_problem_status',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('attempted', 'solved', name='problem_solve_status'), server_default='attempted', nullable=False),
        sa.Column('last_submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'problem_id')
    )
    op.create_index('idx_user_problem_status_user_id', 'user_problem_status', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('user_problem_status')
    op.drop_table('submissions')
    op.drop_table('test_cases')
    op.drop_table('problem_templates')
    op.drop_table('problem_tags')
    op.drop_table('tags')
    op.drop_table('problems')
    op.drop_table('users')

    op.execute('DROP TYPE IF EXISTS problem_solve_status')
    op.execute('DROP TYPE IF EXISTS submission_status')
    op.execute('DROP TYPE IF EXISTS submission_kind')
    op.execute('DROP TYPE IF EXISTS problem_difficulty')
    op.execute('DROP TYPE IF EXISTS user_role')
