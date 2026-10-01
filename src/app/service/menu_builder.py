"""A week menu from the recipes: which dish goes to which meal. Pure logic, no database.

Every day has breakfast, lunch and dinner, each from the recipes that fit that meal.
A dinner that is meant to be cooked x2 (its recipe has a batch note) is cooked x2, and the
second half is tomorrow's lunch; after any other dinner, lunch is a recipe of its own.
Dishes rotate: the least used one goes next, preferably not one already eaten that day or
at the same meal the day before or after; ties are broken at random.

A menu can also be cooked from what's at home (`Stock`): then only dishes there is enough
for go in, every dish takes its products out of the stock as it goes in, and meals nothing
is left for stay empty.
"""

from __future__ import annotations

import datetime as dt
import random
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

MEALS = ("breakfast", "lunch", "dinner")
BATCH_NOTE = "половина — на обед завтра"
LEFTOVERS = " со вчера"          # 'Плов с курицей со вчера'
ONE_DAY = dt.timedelta(days=1)
# How much of each product is enough to cook a dish from what's at home: 450 g of mince
# for 500 g still makes the dish.
ENOUGH = 0.9


@dataclass(frozen=True)
class Dish:
    """A recipe as the menu sees it."""

    id: int
    title: str
    meals: frozenset[str]
    batch: bool = False         # a dinner cooked x2: the second half is tomorrow's lunch
    # products one cooking takes, in their base units; spices, oil and water aren't products
    needs: dict[str, float] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class Slot:
    """One meal of the menu, as a MealPlan row."""

    day: dt.date
    meal: str
    dish: Dish | None           # None: leftovers of yesterday's dinner, a café, nothing planned
    multiplier: float = 1
    note: str = ""
    cooked: bool = False

    @property
    def leftovers(self) -> bool:
        return self.dish is None and self.note.endswith(LEFTOVERS)


class Stock:
    """What's at home for a menu to cook from: every dish put in takes its products out."""

    def __init__(self, have: dict[str, float]):
        self.left = {key: amount for key, amount in have.items() if amount > 0}

    def short(self, dish: Dish, multiplier: float = 1) -> list[str]:
        """The products there isn't enough of for the dish."""
        return [key for key, need in dish.needs.items() if self.left.get(key, 0) < need * multiplier * ENOUGH]

    def fits(self, dish: Dish, multiplier: float = 1) -> bool:
        return not self.short(dish, multiplier)

    def take(self, slot: Slot) -> None:
        if slot.dish:
            for key, need in slot.dish.needs.items():
                self.left[key] = max(self.left.get(key, 0) - need * slot.multiplier, 0)


def cook(day: dt.date, meal: str, dish: Dish, stock: Stock | None = None) -> Slot:
    """From what's at home, a batch dinner is cooked x1 if there is enough for one cooking only;
    a dish that has to be bought anyway is cooked x2 as usual."""
    if meal == "dinner" and dish.batch and not (stock and stock.fits(dish) and not stock.fits(dish, 2)):
        return Slot(day, meal, dish, 2, BATCH_NOTE)
    return Slot(day, meal, dish)


def leftovers_of(dinner: Dish, day: dt.date) -> Slot:
    return Slot(day, "lunch", None, 1, f"{dinner.title}{LEFTOVERS}")


def _ids(slots) -> set[int]:
    return {s.dish.id for s in slots if s and s.dish}


def _pick(options: list[Dish], uses: Counter[int], rng: random.Random, *avoid: set[int]) -> Dish | None:
    """The least used of the options, keeping clear of the `avoid` sets while there is a choice;
    the first set is given up last."""
    for keep in range(len(avoid), -1, -1):
        banned = set().union(*avoid[:keep])
        if pool := [d for d in options if d.id not in banned]:
            least = min(uses[d.id] for d in pool)
            return rng.choice([d for d in pool if uses[d.id] == least])
    return None


def build_week(dishes: list[Dish], start: dt.date, rng: random.Random, days: int = 7,
               before: Slot | None = None, stock: Stock | None = None, cooked: Iterable[Slot] = ()) -> list[Slot]:
    """The menu for `days` days from `start`. `before` is the dinner on the eve of the menu:
    cooked x2, it makes the first lunch. `cooked`: meals of these days already cooked, they stay
    as they are. With `stock`, only from what's at home: the stock is used up as the menu goes,
    meals it isn't enough for are left out."""
    pools = {meal: [d for d in dishes if meal in d.meals] for meal in MEALS}
    done = {(s.day, s.meal): s for s in cooked}
    uses: Counter[int] = Counter()
    week: list[Slot] = []
    yesterday: dict[str, Slot] = {"dinner": before} if before else {}
    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        today: dict[str, Slot] = {}
        for meal in MEALS:
            dinner = yesterday.get("dinner")
            if slot := done.get((day, meal)):
                if slot.dish:
                    uses[slot.dish.id] += 1
            elif meal == "lunch" and dinner and dinner.dish and dinner.multiplier >= 2:
                slot = leftovers_of(dinner.dish, day)
            else:
                near = (yesterday.get(meal), dinner if meal == "lunch" else None)
                options = [d for d in pools[meal] if stock is None or stock.fits(d)]
                dish = _pick(options, uses, rng, _ids(today.values()), _ids(near))
                if dish is None:
                    continue
                uses[dish.id] += 1
                slot = cook(day, meal, dish, stock)
                if stock:
                    stock.take(slot)
            today[meal] = slot
            week.append(slot)
        yesterday = today
    return week


def swap(week: list[Slot], slot: Slot, dishes: list[Dish], rng: random.Random,
         stock: Stock | None = None) -> list[Slot] | None:
    """Another dish instead of the one in `slot` (or a dish for an empty one); None if there is
    nothing else for that meal. Returns the changed slots: a new dinner also decides tomorrow's
    lunch (leftovers or a dish). With `stock`, a dish there is enough for at home after the rest
    of the menu goes first; if there is none, one with the fewest products to buy."""
    at = {(s.day, s.meal): s for s in week}
    uses = Counter(s.dish.id for s in week if s.dish and s is not slot)
    if stock:
        for s in week:
            if s is not slot and not s.cooked:
                stock.take(s)

    def choose(day: dt.date, meal: str, exclude: Dish | None = None) -> Dish | None:
        same_day = [at.get((day, m)) for m in MEALS if m != meal]
        near = [at.get((day - ONE_DAY, meal)), at.get((day + ONE_DAY, meal)),
                at.get((day - ONE_DAY, "dinner")) if meal == "lunch" else None]
        options = [d for d in dishes if meal in d.meals and not (exclude and d.id == exclude.id)]
        if stock and options:
            # not one eaten that day if there is another; of those, the fewest products to buy
            options = [d for d in options if d.id not in _ids(same_day)] or options
            short = {d.id: len(stock.short(d)) for d in options}
            options = [d for d in options if short[d.id] == min(short.values())]
        return _pick(options, uses, rng, _ids(same_day), _ids(near))

    dish = choose(slot.day, slot.meal, exclude=slot.dish)
    if dish is None:
        return None
    new = cook(slot.day, slot.meal, dish, stock)
    if stock:
        stock.take(new)
    changed = [new]
    lunch = at.get((slot.day + ONE_DAY, "lunch"))
    if slot.meal == "dinner" and lunch and not lunch.cooked:
        at[(new.day, new.meal)] = new
        if new.multiplier >= 2:
            changed.append(leftovers_of(dish, lunch.day))
        elif lunch.leftovers and (own := choose(lunch.day, "lunch")):
            changed.append(cook(lunch.day, "lunch", own))
    return changed


def shortages(week: list[Slot], stock: Stock) -> dict[tuple[dt.date, str], list[str]]:
    """Meals of a menu cooked from what's at home that the stock isn't enough for, taken in the
    order they are eaten: the products short for each."""
    short = {}
    for s in week:
        if s.dish and not s.cooked:
            if keys := stock.short(s.dish, s.multiplier):
                short[(s.day, s.meal)] = keys
            stock.take(s)
    return short
