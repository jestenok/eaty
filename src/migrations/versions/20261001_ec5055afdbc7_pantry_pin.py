"""pantry pin: products that should always be at home («Всегда дома»)

Revision ID: ec5055afdbc7
Revises: 1ff296ee0326
Create Date: 2026-10-01 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec5055afdbc7'
down_revision: Union[str, Sequence[str], None] = '1ff296ee0326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pantry_pin',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('product_key', sa.String(length=64), nullable=False),
    sa.Column('min_amount', sa.Numeric(asdecimal=False), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('min_amount is null or min_amount > 0', name=op.f('ck_pantry_pin_min_amount_positive')),
    sa.ForeignKeyConstraint(['product_key'], ['product.key'], name=op.f('fk_pantry_pin_product_key_product'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_pantry_pin_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'product_key', name=op.f('pk_pantry_pin'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pantry_pin')
