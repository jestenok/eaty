"""Built-in data: products with their usual Wolt items, recipes and the first week plan."""

import datetime as dt

from app.repositories.meal_plans import MealPlanRepository
from app.repositories.products import ProductRepository
from app.repositories.recipes import RecipeRepository
from app.repositories.wolt_items import WoltItemRepository
from app.utils.units import parse_amount
from data import recipes as recipes_data


class SeedService:
    def __init__(self, products: ProductRepository, items: WoltItemRepository, recipes: RecipeRepository,
                 plans: MealPlanRepository):
        self.products = products
        self.items = items
        self.recipes = recipes
        self.plans = plans

    async def seed(self, today: dt.date) -> None:
        """Idempotent: refreshes built-in products and recipes, plans a week only if there's no plan."""
        await self.seed_products()
        await self.seed_recipes()
        if await self.plans.is_empty():
            await self.plans.insert_missing(recipes_data.default_week(today, await self.recipes.ids_by_slug()))

    async def seed_products(self) -> None:
        for p in recipes_data.PRODUCTS:
            await self.products.upsert(
                dict(key=p["key"], name=p["name"], base_unit=p["base_unit"], venue_slug=p["venue"],
                     search_q=p["search_q"], match_re=p["match"], exclude_re=p["exclude"]),
                conflict=["key"])
            item_id, name, price, unit_info, step_g = p["preferred"]
            if step_g:  # sold by weight: price is per kg, one "pack" is one weight step
                pack, pack_price = float(step_g), round(price * step_g / 1000)
            else:
                pack, pack_price = parse_amount(unit_info)[0], price
            await self.items.save_preferred(dict(
                id=item_id, venue_slug=p["venue"], name=name, product_key=p["key"], price=pack_price,
                pack_amount=pack, weight_step_g=step_g))

    async def seed_recipes(self) -> None:
        for r in recipes_data.RECIPES:
            recipe_id = await self.recipes.upsert_by_slug(dict(
                slug=r["slug"], title=r["title"], portions=2, appliance=r["appliance"], batch_note=r.get("batch_note", "")))
            await self.recipes.replace_contents(recipe_id, r["ingredients"], r["steps"])
