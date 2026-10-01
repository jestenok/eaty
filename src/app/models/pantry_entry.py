import datetime as dt

from core.db import AMOUNT, Base, CheckConstraint, DateTime, ForeignKey, Index, Mp, String, Text, func, mc, text


class PantryEntry(Base):
    """What's at home, as a ledger: purchases add, cooking subtracts, corrections fix."""

    id: Mp[int] = mc(primary_key=True)
    product_key: Mp[str] = mc(ForeignKey("product.key"), index=True)
    amount: Mp[float] = mc(AMOUNT)                          # base unit; negative = used up
    source: Mp[str] = mc(String(16))                        # order | manual | cooked | correction
    ref: Mp[str | None] = mc(Text)                          # 'order:<id>:<pos>', 'meal:<day>:<meal>'
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("source in ('order', 'manual', 'cooked', 'correction')", name="source"),
        # One entry per order line / cooked meal and product, so re-imports don't double up.
        Index("uq_pantry_entry_ref_product", "ref", "product_key", unique=True, postgresql_where=text("ref is not null")),
    )
