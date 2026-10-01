"""Orders sent by the Chrome extension: store them and put the groceries into the pantry."""

import datetime as dt
from typing import Any

from app.models import WoltSyncLog
from app.repositories.pantry_entries import PantryEntryRepository
from app.repositories.products import ProductRepository
from app.repositories.wolt_items import WoltItemRepository
from app.repositories.wolt_orders import WoltOrderRepository
from app.repositories.wolt_sync_logs import WoltSyncLogRepository
from app.schemas.wolt_order import ImportResultOut, SyncLogIn, SyncLogOut, WoltOrderIn, WoltOrderOut
from app.utils.matching import matches
from app.utils.units import parse_amount
from app.utils.venues import venue_kind
from core.service import BaseService


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


class OrderService(BaseService[WoltOrderRepository]):
    def __init__(self, repository: WoltOrderRepository, items: WoltItemRepository, products: ProductRepository,
                 pantry: PantryEntryRepository, sync_logs: WoltSyncLogRepository, *,
                 grocery_re: str, max_age_days: int):
        super().__init__(repository)
        self.items = items
        self.products = products
        self.pantry = pantry
        self.sync_logs = sync_logs
        self.grocery_re = grocery_re
        self.max_age_days = max_age_days

    async def log_sync(self, dto: SyncLogIn) -> SyncLogOut:
        """What a «Обновить из Wolt» run found; kept to fix the parser if Wolt changes its format."""
        return SyncLogOut.model_validate(await self.sync_logs.add(WoltSyncLog(**dto.model_dump())))

    async def sync_history(self, limit: int) -> list[SyncLogOut]:
        return [SyncLogOut.model_validate(log) for log in await self.sync_logs.latest(limit)]

    async def latest(self, limit: int) -> list[WoltOrderOut]:
        return [WoltOrderOut.model_validate(o) for o in await self.repository.latest(limit)]

    def _filter(self, orders: list[WoltOrderIn], result: ImportResultOut) -> list[WoltOrderIn]:
        """Only recent orders from grocery stores: restaurants and old orders are skipped."""
        oldest = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=self.max_age_days)
        kept = []
        for order in orders:
            kind = venue_kind(product_line=order.product_line, venue_url=order.venue_url,
                              venue_name=order.venue_name, grocery_re=self.grocery_re)
            ordered_at = parse_time(order.ordered_at)
            if kind == "restaurant":
                result.skipped_restaurants += 1
            elif kind == "unknown":
                result.skipped_unknown += 1
            elif ordered_at and ordered_at < oldest:
                result.skipped_old += 1
            else:
                kept.append(order)
        return kept

    async def import_orders(self, orders: list[WoltOrderIn]) -> ImportResultOut:
        result = ImportResultOut(orders=0, pantry_items=0)
        orders = self._filter(orders, result)
        known = await self.items.by_ids([i.id for o in orders for i in o.items if i.id])
        products = await self.products.all()

        def product_for(item_id: str | None, name: str) -> tuple[str | None, float | None]:
            """Product and pack size: by a known Wolt item first, then by the name."""
            item = known.get(item_id or "")
            if item and item.product_key:
                return item.product_key, item.pack_amount
            for p in products:
                if matches(name, p.match_re, p.exclude_re):
                    amount = parse_amount(name)
                    return p.key, amount[0] if amount and amount[1] == p.base_unit else None
            return None, None

        for order in orders:
            lines, entries = [], []
            for pos, item in enumerate(order.items):
                key, pack = product_for(item.id, item.name)
                count = item.count if item.count and item.count > 0 else 1
                lines.append(dict(wolt_item_id=item.id, name=item.name.strip(), count=count, grams=item.grams,
                                  price=round(item.price) if item.price is not None else None, product_key=key))
                amount = item.grams or (count * pack if pack else None)
                if key and amount:
                    entries.append((key, amount, f"order:{order.id}:{pos}"))
            await self.repository.save(
                dict(id=order.id, venue_name=order.venue_name or "", ordered_at=parse_time(order.ordered_at),
                     total=round(order.total) if order.total is not None else None,
                     raw=order.raw or order.model_dump(mode="json", exclude={"raw"})),
                lines)
            for key, amount, ref in entries:
                result.pantry_items += await self.pantry.add_once(key, amount, "order", ref)
        result.orders = len(orders)
        return result
