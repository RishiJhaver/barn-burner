"""Add unique constraint and index to users.username

Revision ID: 0002_add_unique_username
Revises: 0001_initial_schema
Create Date: 2026-09-13 14:24:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_unique_username'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_users_username', 'users', ['username'])
    op.create_index('idx_users_username', 'users', ['username'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_users_username', table_name='users')
    op.drop_constraint('uq_users_username', 'users', type_='unique')
