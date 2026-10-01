import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

Meal = Literal["breakfast", "lunch", "dinner"]


class PlanRowOut(BaseModel):
    day: dt.date
    meal: Meal
    recipe_id: int | None
    multiplier: float
    note: str
    cooked_at: dt.datetime | None
    title: str | None
    slug: str | None
    appliance: str | None


class PlanRowIn(BaseModel):
    recipe_id: int | None = None
    multiplier: float = Field(1, gt=0, le=10)
    note: str = Field("", max_length=200)


class CookedIn(BaseModel):
    cooked: bool


class WeekIn(BaseModel):
    start: dt.date
