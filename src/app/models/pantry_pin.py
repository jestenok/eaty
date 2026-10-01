import datetime as dt

from core.db import AMOUNT, Base, CheckConstraint, DateTime, ForeignKey, Mp, mc, func


class PantryPin(Base):
    """A product that should always be at home («Всегда дома»): when it runs out, it shows up
    at the top of the pantry tab — the list to take to the shop."""

    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    product_key: Mp[str] = mc(ForeignKey("product.key", ondelete="CASCADE"), primary_key=True)
    min_amount: Mp[float | None] = mc(AMOUNT)               # base unit; less is "running low", none = only when out
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("min_amount is null or min_amount > 0", name="min_amount_positive"),)
