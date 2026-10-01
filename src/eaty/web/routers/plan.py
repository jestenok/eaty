import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from eaty.web import seed
from eaty.web.db import get_session
from eaty.web.models import MealPlan, Recipe
from eaty.web.schemas import CookedUpdate, Meal, PlanRow, PlanUpdate, WeekRequest
from eaty.web.services import pantry

router = APIRouter(prefix="/api/plan", tags=["plan"])
Session = Annotated[AsyncSession, Depends(get_session)]
MEAL_ORDER = case({"breakfast": 0, "lunch": 1, "dinner": 2}, value=MealPlan.meal)


async def plan_rows(session: AsyncSession, start: dt.date, days: int) -> list[PlanRow]:
    rows = await session.scalars(
        select(MealPlan)
        .where(MealPlan.day >= start, MealPlan.day < start + dt.timedelta(days=days))
        .order_by(MealPlan.day, MEAL_ORDER))
    return [
        PlanRow(day=p.day, meal=p.meal, recipe_id=p.recipe_id, multiplier=p.multiplier, note=p.note,
                cooked_at=p.cooked_at, title=p.recipe and p.recipe.title, slug=p.recipe and p.recipe.slug,
                appliance=p.recipe and p.recipe.appliance)
        for p in rows.unique()
    ]


@router.get("", response_model=list[PlanRow])
async def get_plan(session: Session, start: dt.date | None = None, days: Annotated[int, Query(ge=1, le=31)] = 7):
    return await plan_rows(session, start or dt.date.today(), days)


@router.put("/{day}/{meal}", response_model=list[PlanRow])
async def put_plan(session: Session, day: dt.date, meal: Meal, body: PlanUpdate):
    if body.recipe_id is not None and await session.get(Recipe, body.recipe_id) is None:
        raise HTTPException(404, "Нет такого рецепта")
    values = dict(day=day, meal=meal, recipe_id=body.recipe_id, multiplier=body.multiplier, note=body.note)
    stmt = insert(MealPlan).values(values)
    await session.execute(stmt.on_conflict_do_update(
        index_elements=[MealPlan.day, MealPlan.meal],
        set_={"recipe_id": stmt.excluded.recipe_id, "multiplier": stmt.excluded.multiplier, "note": stmt.excluded.note}))
    await session.commit()
    return await plan_rows(session, day, 1)


@router.post("/week", response_model=list[PlanRow])
async def fill_week(session: Session, body: WeekRequest):
    """Fill empty meals of the 7 days from `start` with the default menu."""
    await seed.plan_week(session, body.start)
    await session.commit()
    return await plan_rows(session, body.start, 7)


@router.post("/{day}/{meal}/cooked", response_model=list[PlanRow])
async def set_cooked(session: Session, day: dt.date, meal: Meal, body: CookedUpdate):
    """Cooking takes the ingredients out of the pantry; undo puts them back."""
    plan = await session.get(MealPlan, (day, meal))
    if plan is None:
        raise HTTPException(404, "Такого приёма пищи нет в плане")
    if body.cooked:
        plan.cooked_at = dt.datetime.now(dt.timezone.utc)
        await pantry.use_for_meal(session, plan)
    else:
        plan.cooked_at = None
        await pantry.return_for_meal(session, plan)
    await session.commit()
    return await plan_rows(session, day, 1)
