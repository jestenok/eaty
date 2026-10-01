"""Orders sent by the Chrome extension: store them and put the groceries into the pantry."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from eaty.catalog import matches
from eaty.units import parse_amount
from eaty.web.models import PantryEntry, Product, WoltItem, WoltOrder, WoltOrderItem
from eaty.web.schemas import ImportResult, IncomingOrder


def parse_time(value: Any) -> dt.datetime | None:
    """Wolt timestamps come as epoch ms, {"$date": ms} or ISO strings."""
    if isinstance(value, dict):
        value = value.get("$date")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 1e11 else value
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


class ProductMatcher:
    """Order line -> product and pack size: by a known Wolt item id first, then by name."""

    def __init__(self, items: dict[str, WoltItem], products: list[Product]):
        self.items = items
        self.products = products

    @classmethod
    async def load(cls, session: AsyncSession, item_ids: list[str]) -> ProductMatcher:
        items = (await session.scalars(select(WoltItem).where(WoltItem.id.in_(item_ids or [""])))).all()
        products = (await session.scalars(select(Product))).all()
        return cls({i.id: i for i in items}, list(products))

    def match(self, item_id: str | None, name: str) -> tuple[str | None, float | None]:
        known = self.items.get(item_id or "")
        if known and known.product_key:
            return known.product_key, known.pack_amount
        for p in self.products:
            if matches(name, p.match_re, p.exclude_re):
                amount = parse_amount(name)
                return p.key, amount[0] if amount else None
        return None, None


async def import_orders(session: AsyncSession, orders: list[IncomingOrder]) -> ImportResult:
    matcher = await ProductMatcher.load(session, [i.id for o in orders for i in o.items if i.id])
    pantry_items = 0
    for order in orders:
        values = dict(id=order.id, venue_name=order.venue_name or "", ordered_at=parse_time(order.ordered_at),
                      total=round(order.total) if order.total is not None else None,
                      raw=order.raw or order.model_dump(mode="json", exclude={"raw"}))
        stmt = insert(WoltOrder).values(values)
        await session.execute(stmt.on_conflict_do_update(
            index_elements=[WoltOrder.id], set_={k: stmt.excluded[k] for k in values if k != "id"}))
        await session.execute(delete(WoltOrderItem).where(WoltOrderItem.order_id == order.id))

        for pos, item in enumerate(order.items):
            key, pack = matcher.match(item.id, item.name)
            count = item.count if item.count and item.count > 0 else 1
            session.add(WoltOrderItem(
                order_id=order.id, position=pos, wolt_item_id=item.id, name=item.name.strip(), count=count,
                grams=item.grams, price=round(item.price) if item.price is not None else None, product_key=key))
            amount = item.grams or (count * pack if pack else None)
            if key and amount:
                added = await session.scalar(
                    insert(PantryEntry)
                    .values(product_key=key, amount=amount, source="order", ref=f"order:{order.id}:{pos}")
                    .on_conflict_do_nothing()
                    .returning(PantryEntry.id))
                pantry_items += added is not None
    await session.commit()
    return ImportResult(orders=len(orders), pantry_items=pantry_items)
