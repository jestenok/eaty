"""ORM models. The schema itself is owned by Alembic migrations (alembic/versions)."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

Amount = Numeric(asdecimal=False)  # grams / ml / pieces, read back as float


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


BASE_UNIT = "base_unit in ('g', 'ml', 'pcs')"


class Product(Base):
    """Something we buy in Wolt and keep at home: 'chicken_legs', 'eggs'…"""

    __tablename__ = "product"
    __table_args__ = (CheckConstraint(BASE_UNIT, name="base_unit"),)

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    base_unit: Mapped[str] = mapped_column(String(3))
    venue_slug: Mapped[str] = mapped_column(Text)        # the store we normally buy it in
    search_q: Mapped[str] = mapped_column(Text)          # query for the Wolt catalog search
    match_re: Mapped[str] = mapped_column(Text)          # item names that count as this product
    exclude_re: Mapped[str] = mapped_column(Text, server_default="")


class Recipe(Base):
    __tablename__ = "recipe"
    __table_args__ = (CheckConstraint("appliance in ('stove', 'air_fryer', 'none')", name="appliance"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(Text)
    portions: Mapped[int] = mapped_column(Integer, server_default="2")
    appliance: Mapped[str] = mapped_column(String(16), server_default="stove")
    batch_note: Mapped[str] = mapped_column(Text, server_default="")   # what to do when cooking it x2

    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        order_by="RecipeIngredient.position", cascade="all, delete-orphan", lazy="selectin")
    steps: Mapped[list[RecipeStep]] = relationship(
        order_by="RecipeStep.position", cascade="all, delete-orphan", lazy="selectin")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredient"
    __table_args__ = (CheckConstraint("unit in ('g', 'ml', 'pcs')", name="unit"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    name: Mapped[str] = mapped_column(Text)
    # null for spices, oil, water: not bought per recipe
    product_key: Mapped[str | None] = mapped_column(ForeignKey("product.key"))
    amount: Mapped[float | None] = mapped_column(Amount)    # in the product's base unit
    unit: Mapped[str | None] = mapped_column(String(3))
    text_amount: Mapped[str] = mapped_column(Text, server_default="")   # '1,5 ст. л.'
    note: Mapped[str] = mapped_column(Text, server_default="")


class RecipeStep(Base):
    __tablename__ = "recipe_step"
    __table_args__ = (CheckConstraint("timer_seconds > 0", name="timer_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    timer_seconds: Mapped[int | None]
    heat: Mapped[str] = mapped_column(Text, server_default="")   # 'средний огонь', '190 °C'


class MealPlan(Base):
    __tablename__ = "meal_plan"
    __table_args__ = (
        CheckConstraint("meal in ('breakfast', 'lunch', 'dinner')", name="meal"),
        CheckConstraint("multiplier > 0", name="multiplier_positive"),
    )

    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    meal: Mapped[str] = mapped_column(String(16), primary_key=True)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipe.id", ondelete="SET NULL"))
    multiplier: Mapped[float] = mapped_column(Amount, server_default="1")
    note: Mapped[str] = mapped_column(Text, server_default="")       # 'Окорочка со вчера'
    cooked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    recipe: Mapped[Recipe | None] = relationship(lazy="joined")


class WoltItem(Base):
    """A product in a Wolt store, from the public catalog (no login needed)."""

    __tablename__ = "wolt_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_slug: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    product_key: Mapped[str | None] = mapped_column(ForeignKey("product.key"), index=True)
    price: Mapped[int]                                       # tetri per pack (or per weight step)
    pack_amount: Mapped[float | None] = mapped_column(Amount)  # pack size in the product's base unit
    weight_step_g: Mapped[int | None]                        # set for items sold by weight
    preferred: Mapped[bool] = mapped_column(server_default="false")
    available: Mapped[bool] = mapped_column(server_default="true")
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WoltOrder(Base):
    """An order the Chrome extension saw on wolt.com."""

    __tablename__ = "wolt_order"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_name: Mapped[str] = mapped_column(Text, server_default="")
    ordered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    total: Mapped[int | None]                                # tetri
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
    imported_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list[WoltOrderItem]] = relationship(
        order_by="WoltOrderItem.position", cascade="all, delete-orphan", lazy="selectin")


class WoltOrderItem(Base):
    __tablename__ = "wolt_order_item"

    order_id: Mapped[str] = mapped_column(ForeignKey("wolt_order.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    wolt_item_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(Text)
    count: Mapped[float] = mapped_column(Amount)
    grams: Mapped[float | None] = mapped_column(Amount)
    price: Mapped[int | None]
    product_key: Mapped[str | None] = mapped_column(ForeignKey("product.key"))


class PantryEntry(Base):
    """What's at home, as a ledger: purchases add, cooking subtracts, corrections fix."""

    __tablename__ = "pantry_entry"
    __table_args__ = (
        CheckConstraint("source in ('order', 'manual', 'cooked', 'correction')", name="source"),
        # One entry per order line / cooked meal and product, so re-imports don't double up.
        Index("uq_pantry_entry_ref_product", "ref", "product_key", unique=True, postgresql_where=text("ref is not null")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_key: Mapped[str] = mapped_column(ForeignKey("product.key"), index=True)
    amount: Mapped[float] = mapped_column(Amount)            # base unit; negative = used up
    source: Mapped[str] = mapped_column(String(16))
    ref: Mapped[str | None] = mapped_column(Text)            # 'order:<id>:<pos>', 'meal:<day>:<meal>'
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
