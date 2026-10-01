from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.models import PantryEntry
from core.repository import UserScopedRepository


class PantryEntryRepository(UserScopedRepository[PantryEntry]):
    model = PantryEntry

    async def levels(self) -> dict[str, float]:
        rows = await self.session.execute(
            select(PantryEntry.product_key, func.sum(PantryEntry.amount)).where(self.mine).group_by(PantryEntry.product_key))
        return {key: float(have) for key, have in rows}

    async def amounts_for_ref(self, ref: str) -> dict[str, float]:
        rows = await self.session.execute(
            select(PantryEntry.product_key, PantryEntry.amount).where(self.mine, PantryEntry.ref == ref))
        return {key: float(amount) for key, amount in rows}

    async def delete_ref(self, ref: str) -> None:
        await self.delete_where(PantryEntry.ref == ref)

    async def add_entries(self, rows: list[dict]) -> None:
        if rows:
            await self.session.execute(insert(PantryEntry).values([{**row, "user_id": self.user_id} for row in rows]))

    async def add_once(self, product_key: str, amount: float, source: str, ref: str) -> bool:
        """Add an entry unless one with this ref already exists; True if it was added."""
        added = await self.session.scalar(
            insert(PantryEntry)
            .values(user_id=self.user_id, product_key=product_key, amount=amount, source=source, ref=ref)
            .on_conflict_do_nothing()
            .returning(PantryEntry.id))
        return added is not None
