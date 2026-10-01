"""timer push: the app's VAPID key, browsers that allowed notifications, timers to push «Готово!» for

Revision ID: 4620172881f3
Revises: 67cb04bd2dc2
Create Date: 2026-10-02 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4620172881f3'
down_revision: Union[str, Sequence[str], None] = '67cb04bd2dc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('push_key',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('private_key', sa.Text(), nullable=False),
    sa.Column('public_key', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_push_key_one_row')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_key'))
    )
    op.create_table('push_subscription',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('endpoint', sa.Text(), nullable=False),
    sa.Column('p256dh', sa.String(length=200), nullable=False),
    sa.Column('auth', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_push_subscription_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_subscription')),
    sa.UniqueConstraint('endpoint', name=op.f('uq_push_subscription_endpoint'))
    )
    op.create_index(op.f('ix_push_subscription_user_id'), 'push_subscription', ['user_id'], unique=False)
    op.create_table('timer_alarm',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('fire_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_timer_alarm_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'key', name=op.f('pk_timer_alarm'))
    )
    op.create_index(op.f('ix_timer_alarm_fire_at'), 'timer_alarm', ['fire_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_timer_alarm_fire_at'), table_name='timer_alarm')
    op.drop_table('timer_alarm')
    op.drop_index(op.f('ix_push_subscription_user_id'), table_name='push_subscription')
    op.drop_table('push_subscription')
    op.drop_table('push_key')
