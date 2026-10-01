from app.repositories.recipes import RecipeRepository
from app.schemas.recipe import IngredientOut, RecipeOut, RecipeShortOut
from app.service.pantry import PantryService
from core.service import BaseService


class RecipeService(BaseService[RecipeRepository]):
    def __init__(self, repository: RecipeRepository, pantry: PantryService):
        super().__init__(repository)
        self.pantry = pantry

    async def list(self) -> list[RecipeShortOut]:
        return [RecipeShortOut.model_validate(r) for r in await self.repository.all()]

    async def get(self, recipe_id: int) -> RecipeOut:
        """The recipe with how much of each ingredient is at home."""
        recipe = await self.repository.get_one(recipe_id)
        have = await self.pantry.levels()
        out = RecipeOut.model_validate(recipe)
        out.ingredients = [
            IngredientOut.model_validate(i).model_copy(update={"have": have.get(i.product_key) if i.product_key else None})
            for i in recipe.ingredients
        ]
        return out
