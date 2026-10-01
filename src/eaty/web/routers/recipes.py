from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eaty.web.db import get_session
from eaty.web.models import Recipe
from eaty.web.schemas import IngredientOut, RecipeOut, RecipeSummary
from eaty.web.services import pantry

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[RecipeSummary])
async def list_recipes(session: Session):
    return (await session.scalars(select(Recipe).order_by(Recipe.title))).all()


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(session: Session, recipe_id: int):
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(404, "Нет такого рецепта")
    have = await pantry.levels(session)
    out = RecipeOut.model_validate(recipe)
    out.ingredients = [
        IngredientOut.model_validate(i).model_copy(update={"have": have.get(i.product_key) if i.product_key else None})
        for i in recipe.ingredients
    ]
    return out
