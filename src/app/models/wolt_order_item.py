from core.db import AMOUNT, Base, ForeignKey, ForeignKeyConstraint, Mp, String, Text, mc


class WoltOrderItem(Base):
    user_id: Mp[int] = mc(primary_key=True)
    order_id: Mp[str] = mc(String(64), primary_key=True)
    position: Mp[int] = mc(primary_key=True)
    wolt_item_id: Mp[str | None] = mc(String(64))
    name: Mp[str] = mc(Text)
    count: Mp[float] = mc(AMOUNT)
    grams: Mp[float | None] = mc(AMOUNT)
    price: Mp[int | None]
    product_key: Mp[str | None] = mc(ForeignKey("product.key"))

    __table_args__ = (
        ForeignKeyConstraint(["user_id", "order_id"], ["wolt_order.user_id", "wolt_order.id"], ondelete="CASCADE"),
    )
