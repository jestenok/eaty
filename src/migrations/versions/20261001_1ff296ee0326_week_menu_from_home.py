"""week menu from home: a menu put together only from what's at home

Revision ID: 1ff296ee0326
Revises: 463489e14bd9
Create Date: 2026-10-01 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ff296ee0326'
down_revision: Union[str, Sequence[str], None] = '463489e14bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('week_menu', sa.Column('from_home', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('week_menu', 'from_home')
