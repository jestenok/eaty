import datetime as dt

from app.models import MealPlan
from app.repositories.meal_plans import MealPlanRepository
from app.repositories.recipes import RecipeRepository
from app.schemas.plan import Meal, PlanRowIn, PlanRowOut
from app.service.pantry import PantryService
from core.service import BaseService
from data import recipes as recipes_data


class PlanService(BaseService[MealPlanRepository]):
    def __init__(self, repository: MealPlanRepository, recipes: RecipeRepository, pantry: PantryService):
        super().__init__(repository)
        self.recipes = recipes
        self.pantry = pantry

    async def get(self, start: dt.date, days: int) -> list[PlanRowOut]:
        return [plan_row_out(p) for p in await self.repository.between(start, days)]

    async def set_meal(self, day: dt.date, meal: Meal, dto: PlanRowIn) -> list[PlanRowOut]:
        if dto.recipe_id is not None:
            await self.recipes.get_one(dto.recipe_id)
        await self.repository.upsert(
            dict(day=day, meal=meal, recipe_id=dto.recipe_id, multiplier=dto.multiplier, note=dto.note),
            conflict=["day", "meal"], update=["recipe_id", "multiplier", "note"])
        return await self._day(day)

    async def fill_week(self, start: dt.date) -> list[PlanRowOut]:
        """The default menu for the empty meals of the 7 days from `start`."""
        await self.repository.insert_missing(recipes_data.default_week(start, await self.recipes.ids_by_slug()))
        return await self.get(start, 7)

    async def set_cooked(self, day: dt.date, meal: Meal, cooked: bool) -> list[PlanRowOut]:
        """Cooking takes the ingredients out of the pantry; undo puts them back."""
        plan = await self.repository.get_one(day, meal)
        if cooked:
            plan.cooked_at = dt.datetime.now(dt.timezone.utc)
            await self.pantry.use_for_meal(plan)
        else:
            plan.cooked_at = None
            await self.pantry.return_for_meal(plan)
        return await self._day(day)

    async def _day(self, day: dt.date) -> list[PlanRowOut]:
        """The day as it is now in this transaction: UPSERTs above bypass the identity map,
        so loaded rows are flushed and expired to be read again."""
        session = self.repository.session
        await session.flush()
        session.expire_all()
        return await self.get(day, 1)


def plan_row_out(p: MealPlan) -> PlanRowOut:
    recipe = p.recipe
    return PlanRowOut(
        day=p.day, meal=p.meal, recipe_id=p.recipe_id, multiplier=p.multiplier, note=p.note, cooked_at=p.cooked_at,
        title=recipe and recipe.title, slug=recipe and recipe.slug, appliance=recipe and recipe.appliance)
