"""Startup: a fresh database gets the standard week planned from today.

Products and recipes live in the database: a migration loads the initial recipe book once
(migrations/data/recipe_book.json), after that they're edited through the API.
"""

import datetime as dt

from app.repositories.meal_plans import MealPlanRepository


class SeedService:
    def __init__(self, plans: MealPlanRepository):
        self.plans = plans

    async def seed(self, today: dt.date) -> None:
        """Plans the standard week only if there's no plan at all."""
        if await self.plans.is_empty():
            await self.plans.fill_from_template(today)
