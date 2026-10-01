import datetime as dt
from typing import Any

from pydantic import BaseModel


class ShoppingItemOut(BaseModel):
    name: str
    price: int
    pack: str
    by_weight: bool
    url: str


class ShoppingLineOut(BaseModel):
    product_key: str
    product: str
    need: str
    have: str
    to_buy: str
    packs: int
    cost: int
    item: ShoppingItemOut | None


class ShoppingStoreOut(BaseModel):
    venue_slug: str
    total: int
    lines: list[ShoppingLineOut]


class ShoppingListOut(BaseModel):
    start: dt.date
    days: int
    prices_updated_at: dt.datetime | None
    stores: list[ShoppingStoreOut]
    enough: list[ShoppingLineOut]
    not_found: list[ShoppingLineOut]
    total: int


class CatalogStatusOut(BaseModel):
    running: bool
    last: dict[str, Any] | None
