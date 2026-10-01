import datetime as dt

from sqlalchemy import Date, case, func, literal, select
from sqlalchemy.dialects.postgresql import insert

from app.models import MealPlan, RecipeIngredient, WeekTemplate
from core.repository import UserScopedRepository

MEAL_ORDER = case({"breakfast": 0, "lunch": 1, "dinner": 2}, value=MealPlan.meal)


class MealPlanRepository(UserScopedRepository[MealPlan]):
    model = MealPlan

    async def between(self, start: dt.date, days: int) -> list[MealPlan]:
        return await self.find(
            MealPlan.day >= start, MealPlan.day < start + dt.timedelta(days=days),
            order_by=[MealPlan.day, MEAL_ORDER])

    async def is_empty(self) -> bool:
        return not await self.exists()

    async def fill_from_template(self, start: dt.date) -> None:
        """The standard week (week_template) on the 7 days from `start`: only meals that
        aren't planned yet, planned ones stay as they are."""
        t = WeekTemplate
        await self.session.execute(
            insert(MealPlan)
            .from_select(["user_id", "day", "meal", "recipe_id", "multiplier", "note"],
                         select(literal(self.user_id), literal(start, Date) + t.day_offset, t.meal, t.recipe_id,
                                t.multiplier, t.note))
            .on_conflict_do_nothing())

    async def clear_uncooked(self, start: dt.date, days: int) -> None:
        await self.delete_where(MealPlan.day >= start, MealPlan.day < start + dt.timedelta(days=days),
                                MealPlan.cooked_at.is_(None))

    async def insert_missing(self, rows: list[dict]) -> None:
        """Add plan rows for meals that aren't planned yet; planned ones stay as they are."""
        if rows:
            rows = [{**row, "user_id": self.user_id} for row in rows]
            await self.session.execute(insert(MealPlan).values(rows).on_conflict_do_nothing())

    async def needs_between(self, start: dt.date, days: int) -> dict[str, float]:
        """Ingredients of the meals not cooked yet, times how many times each is cooked."""
        rows = await self.session.execute(
            select(RecipeIngredient.product_key, func.sum(RecipeIngredient.amount * MealPlan.multiplier))
            .join(MealPlan, MealPlan.recipe_id == RecipeIngredient.recipe_id)
            .where(self.mine, MealPlan.day >= start, MealPlan.day < start + dt.timedelta(days=days),
                   MealPlan.cooked_at.is_(None), RecipeIngredient.product_key.is_not(None))
            .group_by(RecipeIngredient.product_key))
        return {key: float(need) for key, need in rows}
