import datetime as dt

from app.models import MealPlan, PantryEntry, Product
from app.repositories.pantry_entries import PantryEntryRepository
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

    def __init__(self, repository: PantryEntryRepository, products: ProductRepository, recipes: RecipeRepository):
        super().__init__(repository)
        self.products = products
        self.recipes = recipes

    async def levels(self) -> dict[str, float]:
        return await self.repository.levels()

    async def items(self) -> list[PantryItemOut]:
        have = await self.levels()
        return [self._item_out(p.key, p.name, p.base_unit, have.get(p.key, 0.0)) for p in await self.products.all()]

    async def set_level(self, product_key: str, amount: float) -> PantryItemOut:
        """'I have this much at home': a correction entry, so the history stays intact."""
        product = await self.products.get_one(product_key)
        current = (await self.levels()).get(product_key, 0.0)
        if amount != current:
            await self.repository.add(PantryEntry(product_key=product_key, amount=amount - current, source="correction"))
        return self._item_out(product.key, product.name, product.base_unit, amount)

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
    def _item_out(key: str, name: str, unit: str, have: float) -> PantryItemOut:
        return PantryItemOut(key=key, name=name, base_unit=unit, have=have, have_text=format_amount(max(have, 0.0), unit))

    @staticmethod
    def _used_out(product: Product, amount: float) -> UsedItemOut:
        return UsedItemOut(key=product.key, name=product.name, base_unit=product.base_unit, amount=amount,
                           amount_text=format_amount(amount, product.base_unit))
