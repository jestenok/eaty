"""Prices from the public Wolt catalog."""

import asyncio
import datetime as dt
import logging
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.wolt_catalog import WoltCatalogClient
from app.models import Product
from app.repositories.products import ProductRepository
from app.repositories.wolt_items import WoltItemRepository
from app.utils.matching import matches
from core.db import Database
from core.service import BaseService

log = logging.getLogger(__name__)


class CatalogService(BaseService[WoltItemRepository]):
    def __init__(self, repository: WoltItemRepository, products: ProductRepository, client: WoltCatalogClient):
        super().__init__(repository)
        self.products = products
        self.client = client

    async def refresh_product(self, product: Product) -> int:
        """Search the product in its store and save the matching items with current prices."""
        items = await self.client.search(product.venue_slug, product.search_q)
        # The pack must be in the product's unit: "Лимон, 1 шт" is not 1 g of lemons.
        seen = [i for i in items if i.pack_amount and i.unit == product.base_unit
                and matches(i.name, product.match_re, product.exclude_re)]
        for item in seen:
            await self.repository.save_found(dict(
                id=item.id, venue_slug=product.venue_slug, name=item.name, product_key=product.key,
                price=item.price, pack_amount=item.pack_amount, weight_step_g=item.weight_step_g))
        await self.repository.mark_gone(product.key, product.venue_slug, [i.id for i in seen])
        return len(seen)


class CatalogRefreshJob:
    """Refreshing all prices takes about a minute (Wolt rate limits), so it runs in the
    background. The job owns its transactions: one per product, so a failure in the
    middle keeps what's already refreshed."""

    def __init__(self, database: Database, service_factory: Callable[[AsyncSession], CatalogService], pause: float):
        self.database = database
        self.service_factory = service_factory   # wiring lives in the composition root, not here
        self.pause = pause
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

    async def stop(self) -> None:
        if self.running:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def _run(self) -> None:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        found = failed = 0
        try:
            async with self.database.transaction() as session:
                products = await self.service_factory(session).products.all()
            for product in products:
                try:
                    async with self.database.transaction() as session:
                        found += await self.service_factory(session).refresh_product(product)
                except httpx.HTTPError as exc:
                    failed += 1
                    log.warning("Каталог Wolt: %s не обновился: %s", product.key, exc)
                await asyncio.sleep(self.pause)
            self.last = {"ok": True, "started_at": started, "products": len(products), "items": found, "failed": failed}
        except Exception as exc:  # shown in the UI; the app keeps working with old prices
            log.exception("Каталог Wolt: обновление упало")
            self.last = {"ok": False, "started_at": started, "error": str(exc)}
