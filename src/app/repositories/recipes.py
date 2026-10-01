from typing import Any

from sqlalchemy import func, select

from app.models import Recipe, RecipeIngredient, RecipeStep
from core.repository import BaseRepository


class RecipeRepository(BaseRepository[Recipe]):
    model = Recipe

    async def all(self) -> list[Recipe]:
        return await self.find(order_by=[Recipe.title])

    async def slug_taken(self, slug: str, except_id: int | None = None) -> bool:
        where = [Recipe.slug == slug]
        if except_id is not None:
            where.append(Recipe.id != except_id)
        return await self.exists(*where)

    async def write(self, recipe: Recipe, values: dict[str, Any], ingredients: list[dict], steps: list[dict]) -> Recipe:
        """Set a new or loaded recipe's fields and replace its ingredients and steps."""
        for field, value in values.items():
            setattr(recipe, field, value)
        recipe.ingredients = [RecipeIngredient(position=p, **i) for p, i in enumerate(ingredients)]
        recipe.steps = [RecipeStep(position=p, **s) for p, s in enumerate(steps)]
        return await self.add(recipe)

    async def delete(self, recipe_id: int) -> None:
        """Ingredients and steps go with it; meals planned with it stay, without a recipe."""
        await self.delete_where(Recipe.id == recipe_id)

    async def product_totals(self, recipe_id: int) -> dict[str, float]:
        """How much of each product one cooking of the recipe takes."""
        rows = await self.session.execute(
            select(RecipeIngredient.product_key, func.sum(RecipeIngredient.amount))
            .where(RecipeIngredient.recipe_id == recipe_id, RecipeIngredient.product_key.is_not(None))
            .group_by(RecipeIngredient.product_key))
        return {key: float(amount) for key, amount in rows}
