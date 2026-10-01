"""Refreshing prices from the Wolt catalog."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eaty.catalog import SEARCH_URL, CatalogItem, matches, parse_item
from eaty.web.models import Product, WoltItem

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eaty/0.2"


class CatalogClient:
    def __init__(self, http: httpx.AsyncClient | None = None, pause: float = 0.6):
        self.http = http or httpx.AsyncClient(
            timeout=20, headers={"User-Agent": USER_AGENT, "Accept-Language": "ru"})
        self.pause = pause

    async def search(self, venue_slug: str, query: str) -> list[CatalogItem]:
        for attempt in range(4):  # Wolt answers 429 when asked too often
            resp = await self.http.post(SEARCH_URL.format(slug=venue_slug), params={"language": "ru"}, json={"q": query})
            if resp.status_code != 429:
                break
            await asyncio.sleep(2 * (attempt + 1))
        resp.raise_for_status()
        items = (parse_item(raw) for raw in resp.json().get("items") or ())
        return [i for i in items if i]

    async def aclose(self) -> None:
        await self.http.aclose()


async def refresh(session: AsyncSession, client: CatalogClient) -> dict[str, int]:
    """Search every product in its store and store the matching items with current prices."""
    products = (await session.scalars(select(Product))).all()
    found = failed = 0
    for p in products:
        try:
            items = await client.search(p.venue_slug, p.search_q)
        except httpx.HTTPError:
            failed += 1
            continue
        seen = [i for i in items if i.pack_amount and matches(i.name, p.match_re, p.exclude_re)]
        for item in seen:
            stmt = insert(WoltItem).values(
                id=item.id, venue_slug=p.venue_slug, name=item.name, product_key=p.key, price=item.price,
                pack_amount=item.pack_amount, weight_step_g=item.weight_step_g, available=True)
            await session.execute(stmt.on_conflict_do_update(index_elements=[WoltItem.id], set_={
                "name": stmt.excluded.name, "price": stmt.excluded.price, "pack_amount": stmt.excluded.pack_amount,
                "weight_step_g": stmt.excluded.weight_step_g, "available": True, "fetched_at": dt.datetime.now(dt.timezone.utc),
            }))
        # Items the search no longer shows are probably sold out. The preferred item stays:
        # Wolt's search ranking is fuzzy and missing it once is not proof it's gone.
        await session.execute(
            update(WoltItem)
            .where(WoltItem.product_key == p.key, WoltItem.venue_slug == p.venue_slug,
                   WoltItem.preferred.is_(False), WoltItem.id.not_in([i.id for i in seen] or [""]))
            .values(available=False))
        await session.commit()
        found += len(seen)
        await asyncio.sleep(client.pause)
    return {"products": len(products), "items": found, "failed": failed}


class CatalogJob:
    """A refresh takes about a minute (Wolt rate limits), so it runs as a background task."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions
        self.task: asyncio.Task | None = None
        self.last: dict[str, Any] | None = None

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    def start(self) -> bool:
        if self.running:
            return False
        self.task = asyncio.create_task(self._run())
        return True

    async def _run(self) -> None:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        client = CatalogClient()
        try:
            async with self.sessions() as session:
                self.last = {"ok": True, "started_at": started, **await refresh(session, client)}
        except Exception as exc:  # shown in the UI; the app keeps working with old prices
            self.last = {"ok": False, "started_at": started, "error": str(exc)}
        finally:
            await client.aclose()
