from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.models import PantryEntry
from core.repository import BaseRepository


class PantryEntryRepository(BaseRepository[PantryEntry]):
    model = PantryEntry

    async def levels(self) -> dict[str, float]:
        rows = await self.session.execute(
            select(PantryEntry.product_key, func.sum(PantryEntry.amount)).group_by(PantryEntry.product_key))
        return {key: float(have) for key, have in rows}

    async def delete_ref(self, ref: str) -> None:
        await self.session.execute(delete(PantryEntry).where(PantryEntry.ref == ref))

    async def add_entries(self, rows: list[dict]) -> None:
        if rows:
            await self.session.execute(insert(PantryEntry).values(rows))

    async def add_once(self, product_key: str, amount: float, source: str, ref: str) -> bool:
        """Add an entry unless one with this ref already exists; True if it was added."""
        added = await self.session.scalar(
            insert(PantryEntry)
            .values(product_key=product_key, amount=amount, source=source, ref=ref)
            .on_conflict_do_nothing()
            .returning(PantryEntry.id))
        return added is not None
