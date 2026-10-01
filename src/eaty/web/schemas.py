"""API request and response schemas."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Meal = Literal["breakfast", "lunch", "dinner"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- plan ----------

class PlanRow(BaseModel):
    day: dt.date
    meal: Meal
    recipe_id: int | None
    multiplier: float
    note: str
    cooked_at: dt.datetime | None
    title: str | None
    slug: str | None
    appliance: str | None


class PlanUpdate(BaseModel):
    recipe_id: int | None = None
    multiplier: float = Field(1, gt=0, le=10)
    note: str = Field("", max_length=200)


class CookedUpdate(BaseModel):
    cooked: bool


class WeekRequest(BaseModel):
    start: dt.date


# ---------- recipes ----------

class RecipeSummary(ORM):
    id: int
    slug: str
    title: str
    appliance: str


class IngredientOut(ORM):
    name: str
    product_key: str | None
    amount: float | None
    unit: str | None
    text_amount: str
    note: str
    have: float | None = None   # at home, in the product's base unit


class StepOut(ORM):
    position: int
    text: str
    timer_seconds: int | None
    heat: str


class RecipeOut(RecipeSummary):
    portions: int
    batch_note: str
    ingredients: list[IngredientOut]
    steps: list[StepOut]


# ---------- shopping ----------

class ShoppingItem(BaseModel):
    name: str
    price: int
    pack: str
    by_weight: bool
    url: str


class ShoppingLine(BaseModel):
    product_key: str
    product: str
    need: str
    have: str
    to_buy: str
    packs: int
    cost: int
    item: ShoppingItem | None


class ShoppingStore(BaseModel):
    venue_slug: str
    total: int
    lines: list[ShoppingLine]


class ShoppingList(BaseModel):
    start: dt.date
    days: int
    prices_updated_at: dt.datetime | None
    stores: list[ShoppingStore]
    enough: list[ShoppingLine]
    not_found: list[ShoppingLine]
    total: int


class CatalogStatus(BaseModel):
    running: bool
    last: dict[str, Any] | None


# ---------- pantry & orders ----------

class PantryItem(BaseModel):
    key: str
    name: str
    base_unit: str
    have: float
    have_text: str


class PantrySet(BaseModel):
    amount: float = Field(ge=0)


class IncomingOrderItem(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=500)
    count: float | None = None
    grams: float | None = None
    price: float | None = None


class IncomingOrder(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    venue_name: str | None = None
    ordered_at: Any = None          # epoch ms, {"$date": ms} or ISO string, as Wolt sends it
    total: float | None = None
    status: str | None = None
    items: list[IncomingOrderItem] = Field(min_length=1)
    raw: dict[str, Any] | None = None


class OrdersIn(BaseModel):
    orders: list[IncomingOrder] = Field(max_length=100)


class ImportResult(BaseModel):
    orders: int
    pantry_items: int


class OrderItemOut(ORM):
    name: str
    count: float
    grams: float | None
    product_key: str | None


class OrderOut(ORM):
    id: str
    venue_name: str
    ordered_at: dt.datetime | None
    total: int | None
    imported_at: dt.datetime
    items: list[OrderItemOut]
