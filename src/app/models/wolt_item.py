import datetime as dt

from core.db import AMOUNT, Base, DateTime, ForeignKey, Mp, String, Text, func, mc


class WoltItem(Base):
    """A product in a Wolt store, from the public catalog (no login needed)."""

    id: Mp[str] = mc(String(64), primary_key=True)
    venue_slug: Mp[str] = mc(Text)
    name: Mp[str] = mc(Text)
    product_key: Mp[str | None] = mc(ForeignKey("product.key"), index=True)
    price: Mp[int]                                          # tetri per pack (or per weight step)
    pack_amount: Mp[float | None] = mc(AMOUNT)              # pack size in the product's base unit
    weight_step_g: Mp[int | None]                           # set for items sold by weight
    preferred: Mp[bool] = mc(server_default="false")
    available: Mp[bool] = mc(server_default="true")
    fetched_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
