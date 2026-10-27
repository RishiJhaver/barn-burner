"""Add custom_input and detailed test results persistence to submissions table

Revision ID: 0004_add_submission_testcase_details
Revises: 0003_add_driver_code
Create Date: 2026-10-27 21:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_add_submission_testcase_details'
down_revision: Union[str, None] = '0003_add_driver_code'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('submissions', sa.Column('custom_input', sa.Text(), nullable=True))
    op.add_column('submissions', sa.Column('passed_test_cases', sa.Integer(), nullable=True))
    op.add_column('submissions', sa.Column('total_test_cases', sa.Integer(), nullable=True))
    op.add_column(
        'submissions',
        sa.Column(
            'sample_results',
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'),
            nullable=True,
        ),
    )
    op.add_column(
        'submissions',
        sa.Column(
            'first_failed_case',
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('submissions', 'first_failed_case')
    op.drop_column('submissions', 'sample_results')
    op.drop_column('submissions', 'total_test_cases')
    op.drop_column('submissions', 'passed_test_cases')
    op.drop_column('submissions', 'custom_input')
