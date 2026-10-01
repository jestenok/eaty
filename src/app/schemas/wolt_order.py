import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from app.schemas import BaseOrmModel


class WoltOrderItemIn(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=500)
    count: float | None = None
    grams: float | None = None
    price: float | None = None


class WoltOrderIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    venue_name: str | None = None
    ordered_at: Any = None          # epoch ms, {"$date": ms} or ISO string, as Wolt sends it
    total: float | None = None
    status: str | None = None
    items: list[WoltOrderItemIn] = Field(min_length=1)
    raw: dict[str, Any] | None = None


class WoltOrdersIn(BaseModel):
    orders: list[WoltOrderIn] = Field(max_length=100)


class ImportResultOut(BaseModel):
    orders: int
    pantry_items: int


class WoltOrderItemOut(BaseOrmModel):
    name: str
    count: float
    grams: float | None
    product_key: str | None


class WoltOrderOut(BaseOrmModel):
    id: str
    venue_name: str
    ordered_at: dt.datetime | None
    total: int | None
    imported_at: dt.datetime
    items: list[WoltOrderItemOut]
