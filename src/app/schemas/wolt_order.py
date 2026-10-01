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
    venue_url: str | None = Field(None, max_length=500)       # wolt.com/…/venue/… or …/restaurant/…
    product_line: str | None = Field(None, max_length=64)     # venue type as Wolt reports it
    ordered_at: Any = None          # epoch ms, {"$date": ms} or ISO string, as Wolt sends it
    total: float | None = None
    status: str | None = None
    items: list[WoltOrderItemIn] = Field(min_length=1)
    raw: dict[str, Any] | None = None


class WoltOrdersIn(BaseModel):
    orders: list[WoltOrderIn] = Field(max_length=100)


class ImportResultOut(BaseModel):
    orders: int                     # imported (stores, recent)
    pantry_items: int
    skipped_restaurants: int = 0
    skipped_unknown: int = 0        # couldn't tell a store from a restaurant
    skipped_old: int = 0


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


class SyncLogIn(BaseModel):
    source: str = Field("button", max_length=16)
    orders_found: int = Field(0, ge=0)
    orders_imported: int = Field(0, ge=0)
    pantry_items: int = Field(0, ge=0)
    error: str | None = Field(None, max_length=1000)
    details: dict[str, Any] | None = None


class SyncLogOut(BaseOrmModel):
    id: int
    created_at: dt.datetime
    source: str
    orders_found: int
    orders_imported: int
    pantry_items: int
    error: str | None
    details: dict[str, Any] | None
