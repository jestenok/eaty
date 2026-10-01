"""pantry entries from orders: one per order and product

Revision ID: d536ba05e545
Revises: e5d5bf9e6564
Create Date: 2026-10-01 16:30:00

Order entries used to be per order line ('order:<id>:<pos>'). The same order can now come
from Wolt's data and from the order page with items in a different order, so entries are per
order and product ('order:<id>'). Old line entries are summed into the new form.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd536ba05e545'
down_revision: Union[str, Sequence[str], None] = 'e5d5bf9e6564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_REF = "^order:.+:[0-9]+$"


def upgrade() -> None:
    op.execute(f"""
        insert into pantry_entry (product_key, amount, source, ref, created_at)
        select product_key, sum(amount), 'order', regexp_replace(ref, ':[0-9]+$', ''), min(created_at)
        from pantry_entry
        where source = 'order' and ref ~ '{OLD_REF}'
        group by product_key, regexp_replace(ref, ':[0-9]+$', '')
        on conflict do nothing
    """)
    op.execute(f"delete from pantry_entry where source = 'order' and ref ~ '{OLD_REF}'")


def downgrade() -> None:
    """The new entries stay: they are valid ledger rows, only not split by line."""
