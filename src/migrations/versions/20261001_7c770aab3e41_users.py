"""users: accounts, sign-ins, and the plan, pantry and Wolt orders per user

Data from before accounts goes to an account with login '' that nobody can sign in to;
the first sign-up takes it over (see AuthService.register).

Revision ID: 7c770aab3e41
Revises: e5d5bf9e6564
Create Date: 2026-10-01 12:06:29.539248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c770aab3e41'
down_revision: Union[str, Sequence[str], None] = 'e5d5bf9e6564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OWNED = ("meal_plan", "pantry_entry", "wolt_order", "wolt_order_item")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('app_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('login', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_app_user')),
    sa.UniqueConstraint('login', name=op.f('uq_app_user_login'))
    )
    op.create_table('login_session',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_login_session_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('token_hash', name=op.f('pk_login_session'))
    )
    op.create_index(op.f('ix_login_session_user_id'), 'login_session', ['user_id'], unique=False)

    # Existing data gets an owner: the account the first sign-up takes over.
    bind = op.get_bind()
    has_data = bind.scalar(sa.text(
        "select exists(select from meal_plan) or exists(select from pantry_entry) or exists(select from wolt_order)"))
    owner = bind.scalar(sa.text("insert into app_user (login, password_hash) values ('', '') returning id")) if has_data else None
    for table in OWNED:
        op.add_column(table, sa.Column('user_id', sa.Integer(), nullable=True))
        if owner is not None:
            op.execute(sa.text(f"update {table} set user_id = :owner").bindparams(owner=owner))
        op.alter_column(table, 'user_id', nullable=False)

    op.drop_constraint(op.f('pk_meal_plan'), 'meal_plan', type_='primary')
    op.create_primary_key(op.f('pk_meal_plan'), 'meal_plan', ['user_id', 'day', 'meal'])
    op.create_foreign_key(op.f('fk_meal_plan_user_id_app_user'), 'meal_plan', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

    op.drop_index(op.f('uq_pantry_entry_ref_product'), table_name='pantry_entry', postgresql_where='(ref IS NOT NULL)')
    op.create_index('uq_pantry_entry_ref_product', 'pantry_entry', ['user_id', 'ref', 'product_key'], unique=True, postgresql_where=sa.text('ref is not null'))
    op.create_index(op.f('ix_pantry_entry_user_id'), 'pantry_entry', ['user_id'], unique=False)
    op.create_foreign_key(op.f('fk_pantry_entry_user_id_app_user'), 'pantry_entry', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

    # Two users may import the same Wolt order: orders are keyed by user too.
    op.drop_constraint(op.f('fk_wolt_order_item_order_id_wolt_order'), 'wolt_order_item', type_='foreignkey')
    op.drop_constraint(op.f('pk_wolt_order_item'), 'wolt_order_item', type_='primary')
    op.drop_constraint(op.f('pk_wolt_order'), 'wolt_order', type_='primary')
    op.create_primary_key(op.f('pk_wolt_order'), 'wolt_order', ['user_id', 'id'])
    op.create_primary_key(op.f('pk_wolt_order_item'), 'wolt_order_item', ['user_id', 'order_id', 'position'])
    op.create_foreign_key(op.f('fk_wolt_order_user_id_app_user'), 'wolt_order', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('fk_wolt_order_item_user_id_wolt_order'), 'wolt_order_item', 'wolt_order', ['user_id', 'order_id'], ['user_id', 'id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema. The single-user schema holds one account: the oldest one's data is kept."""
    keep = op.get_bind().scalar(sa.text("select min(id) from app_user"))
    for table in ("meal_plan", "pantry_entry", "wolt_order"):  # order lines go with their orders
        op.execute(sa.text(f"delete from {table} where user_id is distinct from :keep").bindparams(keep=keep))

    op.drop_constraint(op.f('fk_wolt_order_item_user_id_wolt_order'), 'wolt_order_item', type_='foreignkey')
    op.drop_constraint(op.f('fk_wolt_order_user_id_app_user'), 'wolt_order', type_='foreignkey')
    op.drop_constraint(op.f('pk_wolt_order_item'), 'wolt_order_item', type_='primary')
    op.drop_constraint(op.f('pk_wolt_order'), 'wolt_order', type_='primary')
    op.create_primary_key(op.f('pk_wolt_order'), 'wolt_order', ['id'])
    op.create_primary_key(op.f('pk_wolt_order_item'), 'wolt_order_item', ['order_id', 'position'])
    op.create_foreign_key(op.f('fk_wolt_order_item_order_id_wolt_order'), 'wolt_order_item', 'wolt_order', ['order_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint(op.f('fk_pantry_entry_user_id_app_user'), 'pantry_entry', type_='foreignkey')
    op.drop_index(op.f('ix_pantry_entry_user_id'), table_name='pantry_entry')
    op.drop_index('uq_pantry_entry_ref_product', table_name='pantry_entry', postgresql_where=sa.text('ref is not null'))
    op.create_index(op.f('uq_pantry_entry_ref_product'), 'pantry_entry', ['ref', 'product_key'], unique=True, postgresql_where='(ref IS NOT NULL)')

    op.drop_constraint(op.f('fk_meal_plan_user_id_app_user'), 'meal_plan', type_='foreignkey')
    op.drop_constraint(op.f('pk_meal_plan'), 'meal_plan', type_='primary')
    op.create_primary_key(op.f('pk_meal_plan'), 'meal_plan', ['day', 'meal'])

    for table in OWNED:
        op.drop_column(table, 'user_id')
    op.drop_index(op.f('ix_login_session_user_id'), table_name='login_session')
    op.drop_table('login_session')
    op.drop_table('app_user')
