import datetime as dt
from typing import Any

from core.db import JSONB, Base, DateTime, ForeignKey, Mp, String, Text, func, mc, relationship


class WoltOrder(Base):
    """An order the Chrome extension saw on wolt.com."""

    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    id: Mp[str] = mc(String(64), primary_key=True)          # Wolt's order id
    venue_name: Mp[str] = mc(Text, server_default="")
    ordered_at: Mp[dt.datetime | None] = mc(DateTime(timezone=True))
    total: Mp[int | None]                                   # tetri
    raw: Mp[dict[str, Any]] = mc(JSONB)
    imported_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())

    items: Mp[list["WoltOrderItem"]] = relationship(
        order_by="WoltOrderItem.position", cascade="all, delete-orphan", lazy="selectin")
