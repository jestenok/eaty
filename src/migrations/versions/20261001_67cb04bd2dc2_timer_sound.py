"""timer sound: the user's own sound for a timer that rings

Revision ID: 67cb04bd2dc2
Revises: ec5055afdbc7
Create Date: 2026-10-01 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67cb04bd2dc2'
down_revision: Union[str, Sequence[str], None] = 'ec5055afdbc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('timer_sound',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_timer_sound_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_timer_sound'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('timer_sound')
