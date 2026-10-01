from app.models import Recipe
from app.repositories.products import ProductRepository
from app.repositories.recipes import RecipeRepository
from app.schemas.recipe import IngredientOut, RecipeIn, RecipeOut, RecipeShortOut
from app.service.pantry import PantryService
from core.error import AppError, ConflictError, NotFoundError
from core.service import BaseService


class RecipeService(BaseService[RecipeRepository]):
    def __init__(self, repository: RecipeRepository, products: ProductRepository, pantry: PantryService):
        super().__init__(repository)
        self.products = products
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

    async def create(self, dto: RecipeIn) -> RecipeOut:
        return await self._write(Recipe(), dto)

    async def update(self, recipe_id: int, dto: RecipeIn) -> RecipeOut:
        """Replaces the whole recipe: fields, ingredients and steps."""
        return await self._write(await self.repository.get_one(recipe_id), dto)

    async def delete(self, recipe_id: int) -> None:
        await self.repository.get_one(recipe_id)
        await self.repository.delete(recipe_id)

    async def _write(self, recipe: Recipe, dto: RecipeIn) -> RecipeOut:
        if await self.repository.slug_taken(dto.slug, except_id=recipe.id):
            raise ConflictError(f"Рецепт со slug «{dto.slug}» уже есть")
        await self._check_products(dto)
        values = dto.model_dump(exclude={"ingredients", "steps"})
        await self.repository.write(recipe, values, [i.model_dump() for i in dto.ingredients],
                                    [s.model_dump() for s in dto.steps])
        return await self.get(recipe.id)

    async def _check_products(self, dto: RecipeIn) -> None:
        """Bought ingredients must be known products in their base unit: the shopping list
        and the pantry add amounts up per product."""
        units = {p.key: p.base_unit for p in await self.products.all()}
        for i in dto.ingredients:
            if i.product_key is None:
                continue
            if i.product_key not in units:
                raise NotFoundError(f"Продукта «{i.product_key}» нет: сначала добавь его в /api/v1/products")
            if i.unit != units[i.product_key]:
                raise AppError(f"{i.name}: продукт «{i.product_key}» считается в {units[i.product_key]}, а не в {i.unit}")
