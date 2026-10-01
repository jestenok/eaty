from sqlalchemy import select

from app.models import PantryPin
from core.repository import UserScopedRepository


class PantryPinRepository(UserScopedRepository[PantryPin]):
    model = PantryPin

    async def all(self) -> dict[str, float | None]:
        """Pinned product -> the least to keep at home (None: only when it's out)."""
        rows = await self.session.execute(select(PantryPin.product_key, PantryPin.min_amount).where(self.mine))
        return {key: None if least is None else float(least) for key, least in rows}

    async def pin(self, product_key: str, min_amount: float | None) -> None:
        await self.upsert(dict(product_key=product_key, min_amount=min_amount), conflict=("product_key",),
                          update=("min_amount",))

    async def unpin(self, product_key: str) -> None:
        await self.delete_where(PantryPin.product_key == product_key)
