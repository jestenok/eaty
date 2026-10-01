from fastapi import APIRouter

from api.dependencies import RecipeServiceDep
from app.schemas.recipe import RecipeOut, RecipeShortOut

router = APIRouter()


@router.get("", summary="Список рецептов", response_model=list[RecipeShortOut])
async def list_recipes(service: RecipeServiceDep):
    return await service.list()


@router.get("/{recipe_id}", summary="Рецепт с шагами и тем, что есть дома", response_model=RecipeOut)
async def get_recipe(service: RecipeServiceDep, recipe_id: int):
    return await service.get(recipe_id)
