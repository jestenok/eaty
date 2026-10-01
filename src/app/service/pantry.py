import datetime as dt

from app.models import MealPlan, PantryEntry, Product
from app.repositories.pantry_entries import PantryEntryRepository
from app.repositories.pantry_pins import PantryPinRepository
from app.repositories.products import ProductRepository
from app.repositories.recipes import RecipeRepository
from app.schemas.pantry import PantryItemOut, UsedItemOut
from app.utils.units import format_amount
from core.error import NotFoundError
from core.service import BaseService


def meal_ref(day: dt.date, meal: str) -> str:
    return f"meal:{day.isoformat()}:{meal}"


class PantryService(BaseService[PantryEntryRepository]):
    """What's at home: purchases add, cooked meals subtract, corrections set the level."""

    def __init__(self, repository: PantryEntryRepository, products: ProductRepository, recipes: RecipeRepository,
                 pins: PantryPinRepository):
        super().__init__(repository)
        self.products = products
        self.recipes = recipes
        self.pins = pins

    async def levels(self) -> dict[str, float]:
        return await self.repository.levels()

    async def items(self) -> list[PantryItemOut]:
        have, pins = await self.levels(), await self.pins.all()
        return [self._item_out(p, have.get(p.key, 0.0), pins) for p in await self.products.all()]

    async def item(self, product_key: str) -> PantryItemOut:
        product = await self.products.get_one(product_key)
        return self._item_out(product, (await self.levels()).get(product_key, 0.0), await self.pins.all())

    async def set_level(self, product_key: str, amount: float) -> PantryItemOut:
        """'I have this much at home': a correction entry, so the history stays intact."""
        await self.products.get_one(product_key)
        current = (await self.levels()).get(product_key, 0.0)
        if amount != current:
            await self.repository.add(PantryEntry(product_key=product_key, amount=amount - current, source="correction"))
        return await self.item(product_key)

    async def pin(self, product_key: str, min_amount: float | None) -> PantryItemOut:
        """«Всегда дома»: keep this product at home (pinning again changes the least to keep)."""
        await self.products.get_one(product_key)
        await self.pins.pin(product_key, min_amount)
        return await self.item(product_key)

    async def unpin(self, product_key: str) -> PantryItemOut:
        await self.products.get_one(product_key)
        await self.pins.unpin(product_key)
        return await self.item(product_key)

    async def use_for_meal(self, plan: MealPlan) -> None:
        """Take the meal's ingredients out of the pantry (replacing an earlier write-off, if any)."""
        totals = await self.recipes.product_totals(plan.recipe_id) if plan.recipe_id is not None else {}
        await self._write_off(plan, {key: amount * plan.multiplier for key, amount in totals.items()})

    async def return_for_meal(self, plan: MealPlan) -> None:
        await self.repository.delete_ref(meal_ref(plan.day, plan.meal))

    async def used_for_meal(self, plan: MealPlan) -> list[UsedItemOut]:
        """What cooking the meal took out of the pantry, by product name."""
        used = await self.repository.amounts_for_ref(meal_ref(plan.day, plan.meal))
        return [self._used_out(p, -used[p.key]) for p in await self.products.all() if p.key in used]

    async def set_used_for_meal(self, plan: MealPlan, amounts: dict[str, float]) -> list[UsedItemOut]:
        """'It really took this much': the meal's write-off is replaced with these amounts."""
        known = {p.key for p in await self.products.all()}
        if unknown := sorted(set(amounts) - known):
            raise NotFoundError(f"Product {', '.join(unknown)} не найден")
        await self._write_off(plan, amounts)
        return await self.used_for_meal(plan)

    async def _write_off(self, plan: MealPlan, amounts: dict[str, float]) -> None:
        ref = meal_ref(plan.day, plan.meal)
        await self.repository.delete_ref(ref)
        await self.repository.add_entries([
            dict(product_key=key, amount=-amount, source="cooked", ref=ref)
            for key, amount in amounts.items() if amount > 0
        ])

    @staticmethod
    def _item_out(product: Product, have: float, pins: dict[str, float | None]) -> PantryItemOut:
        unit, pinned, least = product.base_unit, product.key in pins, pins.get(product.key)
        return PantryItemOut(
            key=product.key, name=product.name, base_unit=unit, have=have, have_text=format_amount(max(have, 0.0), unit),
            pinned=pinned, min_amount=least, min_text=format_amount(least, unit) if least else "",
            missing=pinned and (have < least if least else have <= 0))

    @staticmethod
    def _used_out(product: Product, amount: float) -> UsedItemOut:
        return UsedItemOut(key=product.key, name=product.name, base_unit=product.base_unit, amount=amount,
                           amount_text=format_amount(amount, product.base_unit))
