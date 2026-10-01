from typing import Any

from sqlalchemy import delete

from app.models import WoltOrder, WoltOrderItem
from core.repository import BaseRepository


class WoltOrderRepository(BaseRepository[WoltOrder]):
    model = WoltOrder

    async def save(self, values: dict[str, Any], items: list[dict[str, Any]]) -> None:
        """Insert or refresh the order and replace its lines (Wolt may send it again)."""
        await self.upsert(values, conflict=["id"])
        await self.session.execute(delete(WoltOrderItem).where(WoltOrderItem.order_id == values["id"]))
        self.session.add_all(WoltOrderItem(order_id=values["id"], position=pos, **item) for pos, item in enumerate(items))
        await self.session.flush()

    async def latest(self, limit: int) -> list[WoltOrder]:
        return await self.find(order_by=[WoltOrder.ordered_at.desc().nulls_last(), WoltOrder.imported_at.desc()],
                               limit=limit)
