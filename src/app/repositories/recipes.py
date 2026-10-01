from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.models import Recipe, RecipeIngredient, RecipeStep
from core.repository import BaseRepository


class RecipeRepository(BaseRepository[Recipe]):
    model = Recipe

    async def all(self) -> list[Recipe]:
        return await self.find(order_by=[Recipe.title])

    async def ids_by_slug(self) -> dict[str, int]:
        return {slug: id_ for slug, id_ in await self.session.execute(select(Recipe.slug, Recipe.id))}

    async def upsert_by_slug(self, values: dict[str, Any]) -> int:
        stmt = insert(Recipe).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Recipe.slug], set_={k: stmt.excluded[k] for k in values if k != "slug"})
        return (await self.session.execute(stmt.returning(Recipe.id))).scalar_one()

    async def replace_contents(self, recipe_id: int, ingredients: list[dict], steps: list[dict]) -> None:
        await self.session.execute(RecipeIngredient.__table__.delete().where(RecipeIngredient.recipe_id == recipe_id))
        await self.session.execute(RecipeStep.__table__.delete().where(RecipeStep.recipe_id == recipe_id))
        self.session.add_all(RecipeIngredient(recipe_id=recipe_id, position=p, **i) for p, i in enumerate(ingredients))
        self.session.add_all(RecipeStep(recipe_id=recipe_id, position=p, **s) for p, s in enumerate(steps))
        await self.session.flush()

    async def product_totals(self, recipe_id: int) -> dict[str, float]:
        """How much of each product one cooking of the recipe takes."""
        rows = await self.session.execute(
            select(RecipeIngredient.product_key, func.sum(RecipeIngredient.amount))
            .where(RecipeIngredient.recipe_id == recipe_id, RecipeIngredient.product_key.is_not(None))
            .group_by(RecipeIngredient.product_key))
        return {key: float(amount) for key, amount in rows}
