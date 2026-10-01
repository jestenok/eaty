from fastapi import APIRouter

from api.dependencies import RecipeServiceDep
from app.schemas.recipe import RecipeIn, RecipeOut, RecipeShortOut

router = APIRouter()


@router.get("", summary="Список рецептов", response_model=list[RecipeShortOut])
async def list_recipes(service: RecipeServiceDep):
    return await service.list()


@router.get("/{recipe_id}", summary="Рецепт с шагами и тем, что есть дома", response_model=RecipeOut)
async def get_recipe(service: RecipeServiceDep, recipe_id: int):
    return await service.get(recipe_id)


@router.post("", status_code=201, summary="Добавить рецепт (на 2 порции)", response_model=RecipeOut)
async def create_recipe(service: RecipeServiceDep, dto: RecipeIn):
    return await service.create(dto)


@router.put("/{recipe_id}", summary="Заменить рецепт целиком: поля, продукты и шаги", response_model=RecipeOut)
async def update_recipe(service: RecipeServiceDep, recipe_id: int, dto: RecipeIn):
    return await service.update(recipe_id, dto)


@router.delete("/{recipe_id}", status_code=204, summary="Удалить рецепт (в плане приём пищи останется без рецепта)")
async def delete_recipe(service: RecipeServiceDep, recipe_id: int) -> None:
    await service.delete(recipe_id)
