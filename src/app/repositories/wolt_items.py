import datetime as dt
from typing import Any

from sqlalchemy import func, select, update

from app.models import WoltItem
from core.repository import BaseRepository


class WoltItemRepository(BaseRepository[WoltItem]):
    model = WoltItem

    async def by_ids(self, ids: list[str]) -> dict[str, WoltItem]:
        if not ids:
            return {}
        return {i.id: i for i in await self.find(WoltItem.id.in_(ids))}

    async def offers(self) -> list[WoltItem]:
        """Items that can be bought now and are tied to a product."""
        return await self.find(WoltItem.available.is_(True), WoltItem.product_key.is_not(None), WoltItem.pack_amount > 0)

    async def last_refresh(self) -> dt.datetime | None:
        return await self.session.scalar(select(func.max(WoltItem.fetched_at)).where(WoltItem.preferred.is_(False)))

    async def save_preferred(self, values: dict[str, Any]) -> None:
        """Built-in favourite item: inserted once, later prices come from catalog refreshes."""
        await self.upsert({**values, "preferred": True}, conflict=["id"], update=["preferred", "product_key"])

    async def save_found(self, values: dict[str, Any]) -> None:
        await self.upsert(
            {**values, "available": True, "fetched_at": dt.datetime.now(dt.timezone.utc)},
            conflict=["id"], update=["name", "price", "pack_amount", "weight_step_g", "available", "fetched_at"])

    async def mark_gone(self, product_key: str, venue_slug: str, seen_ids: list[str]) -> None:
        """Items the search no longer shows are probably sold out. The preferred item stays:
        Wolt's search ranking is fuzzy and missing it once is not proof it's gone."""
        await self.session.execute(
            update(WoltItem)
            .where(WoltItem.product_key == product_key, WoltItem.venue_slug == venue_slug,
                   WoltItem.preferred.is_(False), WoltItem.id.not_in(seen_ids or [""]))
            .values(available=False))
