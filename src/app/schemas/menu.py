import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.schemas import BaseOrmModel
from app.schemas.plan import PlanRowOut
from app.schemas.shopping import ShoppingListOut

MenuStatus = Literal["draft", "awaiting_order", "ordered"]


class MenuIn(BaseModel):
    start: dt.date
    # only from what's at home, minus what the other planned meals will take
    from_home: bool = False


class MenuStatusIn(BaseModel):
    status: MenuStatus


class MenuMealOut(PlanRowOut):
    swappable: bool             # a draft's dish that isn't cooked yet
    # a menu from home: the products there isn't enough of at home for this meal
    missing: list[str] = []


class MenuOrderLinkOut(BaseOrmModel):
    id: str
    venue_name: str
    ordered_at: dt.datetime | None
    total: int | None


class MenuOut(BaseModel):
    id: int
    start: dt.date
    last_day: dt.date
    status: MenuStatus
    from_home: bool
    created_at: dt.datetime
    confirmed_at: dt.datetime | None
    ordered_at: dt.datetime | None
    meals: list[MenuMealOut]
    orders: list[MenuOrderLinkOut]     # Wolt orders placed for this menu


class MenuOrderOut(BaseModel):
    """What to order in Wolt so that everything planned until the menu's last day is at home."""

    menu_id: int
    status: MenuStatus
    first_day: dt.date
    last_day: dt.date
    shopping: ShoppingListOut
    task: str                   # the same as text, for Claude in a browser

