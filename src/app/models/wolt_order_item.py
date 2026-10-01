from core.db import AMOUNT, Base, ForeignKey, Mp, String, Text, mc


class WoltOrderItem(Base):
    order_id: Mp[str] = mc(ForeignKey("wolt_order.id", ondelete="CASCADE"), primary_key=True)
    position: Mp[int] = mc(primary_key=True)
    wolt_item_id: Mp[str | None] = mc(String(64))
    name: Mp[str] = mc(Text)
    count: Mp[float] = mc(AMOUNT)
    grams: Mp[float | None] = mc(AMOUNT)
    price: Mp[int | None]
    product_key: Mp[str | None] = mc(ForeignKey("product.key"))
