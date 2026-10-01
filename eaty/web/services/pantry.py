"""What's at home: a ledger of purchases (+), cooked meals (-) and manual corrections."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from eaty.web.models import MealPlan, PantryEntry, RecipeIngredient


async def levels(session: AsyncSession) -> dict[str, float]:
    rows = await session.execute(
        select(PantryEntry.product_key, func.sum(PantryEntry.amount)).group_by(PantryEntry.product_key))
    return {key: float(have) for key, have in rows}


def meal_ref(day: dt.date, meal: str) -> str:
    return f"meal:{day.isoformat()}:{meal}"


async def use_for_meal(session: AsyncSession, plan: MealPlan) -> None:
    """Take the meal's ingredients out of the pantry (replacing an earlier write-off, if any)."""
    ref = meal_ref(plan.day, plan.meal)
    await session.execute(delete(PantryEntry).where(PantryEntry.ref == ref))
    if plan.recipe_id is None:
        return
    used = await session.execute(
        select(RecipeIngredient.product_key, func.sum(RecipeIngredient.amount))
        .where(RecipeIngredient.recipe_id == plan.recipe_id, RecipeIngredient.product_key.is_not(None))
        .group_by(RecipeIngredient.product_key))
    rows = [dict(product_key=key, amount=-float(amount) * plan.multiplier, source="cooked", ref=ref)
            for key, amount in used]
    if rows:
        await session.execute(insert(PantryEntry).values(rows))


async def return_for_meal(session: AsyncSession, plan: MealPlan) -> None:
    await session.execute(delete(PantryEntry).where(PantryEntry.ref == meal_ref(plan.day, plan.meal)))


async def set_level(session: AsyncSession, product_key: str, amount: float) -> None:
    """'I have this much at home': a correction entry, so the history stays intact."""
    current = (await levels(session)).get(product_key, 0.0)
    if amount != current:
        session.add(PantryEntry(product_key=product_key, amount=amount - current, source="correction"))
