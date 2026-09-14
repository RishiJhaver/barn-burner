"""Add driver_code to problem_templates table

Revision ID: 0003_add_driver_code
Revises: 0002_add_unique_username
Create Date: 2026-09-13 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_add_driver_code'
down_revision: Union[str, None] = '0002_add_unique_username'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('problem_templates', sa.Column('driver_code', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('problem_templates', 'driver_code')
