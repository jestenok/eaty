"""Built-in data: products with their usual Wolt items, recipes, and a default week plan."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from eaty import recipes_data
from eaty.units import parse_amount
from eaty.web.models import MealPlan, Product, Recipe, RecipeIngredient, RecipeStep, WoltItem


async def seed(session: AsyncSession, today: dt.date | None = None) -> None:
    """Idempotent: refreshes built-in products and recipes, plans a week only if there's no plan."""
    await seed_products(session)
    await seed_recipes(session)
    if (await session.execute(select(MealPlan.day).limit(1))).first() is None:
        await plan_week(session, today or dt.date.today())
    await session.commit()


async def seed_products(session: AsyncSession) -> None:
    for p in recipes_data.PRODUCTS:
        values = dict(key=p["key"], name=p["name"], base_unit=p["base_unit"], venue_slug=p["venue"],
                      search_q=p["search_q"], match_re=p["match"], exclude_re=p["exclude"])
        stmt = insert(Product).values(values)
        await session.execute(stmt.on_conflict_do_update(
            index_elements=[Product.key], set_={k: stmt.excluded[k] for k in values if k != "key"}))

        item_id, name, price, unit_info, step_g = p["preferred"]
        if step_g:  # sold by weight: price is per kg, one "pack" is one weight step
            pack, pack_price = float(step_g), round(price * step_g / 1000)
        else:
            pack, pack_price = parse_amount(unit_info)[0], price
        item = insert(WoltItem).values(id=item_id, venue_slug=p["venue"], name=name, product_key=p["key"],
                                       price=pack_price, pack_amount=pack, weight_step_g=step_g, preferred=True)
        # Prices refreshed from Wolt later must not be overwritten by these defaults.
        await session.execute(item.on_conflict_do_update(
            index_elements=[WoltItem.id], set_={"preferred": True, "product_key": item.excluded.product_key}))


async def seed_recipes(session: AsyncSession) -> None:
    for r in recipes_data.RECIPES:
        values = dict(slug=r["slug"], title=r["title"], portions=2, appliance=r["appliance"],
                      batch_note=r.get("batch_note", ""))
        stmt = insert(Recipe).values(values)
        recipe_id = (await session.execute(
            stmt.on_conflict_do_update(index_elements=[Recipe.slug],
                                       set_={k: stmt.excluded[k] for k in values if k != "slug"})
            .returning(Recipe.id))).scalar_one()
        await session.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id))
        await session.execute(delete(RecipeStep).where(RecipeStep.recipe_id == recipe_id))
        session.add_all(RecipeIngredient(recipe_id=recipe_id, position=pos, **i) for pos, i in enumerate(r["ingredients"]))
        session.add_all(RecipeStep(recipe_id=recipe_id, position=pos, **s) for pos, s in enumerate(r["steps"]))
    await session.flush()


async def plan_week(session: AsyncSession, start: dt.date) -> None:
    """Fill the 7 days from `start` with the default menu; days already planned stay as they are."""
    ids = {slug: id_ for slug, id_ in await session.execute(select(Recipe.slug, Recipe.id))}
    rows = [
        dict(day=start + dt.timedelta(days=offset), meal=meal, recipe_id=ids.get(slug) if slug else None,
             multiplier=multiplier, note=note)
        for offset, meals in enumerate(recipes_data.WEEK_TEMPLATE)
        for meal, (slug, multiplier, note) in meals.items()
    ]
    await session.execute(insert(MealPlan).values(rows).on_conflict_do_nothing())
