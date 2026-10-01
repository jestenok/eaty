"""A week menu from the recipes: which dish goes to which meal. Pure logic, no database.

Every day has breakfast, lunch and dinner, each from the recipes that fit that meal.
A dinner that is meant to be cooked x2 (its recipe has a batch note) is cooked x2, and the
second half is tomorrow's lunch; after any other dinner, lunch is a recipe of its own.
Dishes rotate: the least used one goes next, preferably not one already eaten that day or
at the same meal the day before or after; ties are broken at random.
"""

from __future__ import annotations

import datetime as dt
import random
from collections import Counter
from dataclasses import dataclass

MEALS = ("breakfast", "lunch", "dinner")
BATCH_NOTE = "половина — на обед завтра"
LEFTOVERS = " со вчера"          # 'Плов с курицей со вчера'
ONE_DAY = dt.timedelta(days=1)


@dataclass(frozen=True)
class Dish:
    """A recipe as the menu sees it."""

    id: int
    title: str
    meals: frozenset[str]
    batch: bool = False         # a dinner cooked x2: the second half is tomorrow's lunch


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


def cook(day: dt.date, meal: str, dish: Dish) -> Slot:
    if meal == "dinner" and dish.batch:
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
               before: Slot | None = None) -> list[Slot]:
    """The menu for `days` days from `start`. `before` is the dinner on the eve of the menu:
    cooked x2, it makes the first lunch."""
    pools = {meal: [d for d in dishes if meal in d.meals] for meal in MEALS}
    uses: Counter[int] = Counter()
    week: list[Slot] = []
    yesterday: dict[str, Slot] = {"dinner": before} if before else {}
    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        today: dict[str, Slot] = {}
        for meal in MEALS:
            dinner = yesterday.get("dinner")
            if meal == "lunch" and dinner and dinner.dish and dinner.multiplier >= 2:
                slot = leftovers_of(dinner.dish, day)
            else:
                near = (yesterday.get(meal), dinner if meal == "lunch" else None)
                dish = _pick(pools[meal], uses, rng, _ids(today.values()), _ids(near))
                if dish is None:
                    continue
                uses[dish.id] += 1
                slot = cook(day, meal, dish)
            today[meal] = slot
            week.append(slot)
        yesterday = today
    return week


def swap(week: list[Slot], slot: Slot, dishes: list[Dish], rng: random.Random) -> list[Slot] | None:
    """Another dish instead of the one in `slot`; None if there is nothing else for that meal.
    Returns the changed slots: a new dinner also decides tomorrow's lunch (leftovers or a dish)."""
    at = {(s.day, s.meal): s for s in week}
    uses = Counter(s.dish.id for s in week if s.dish and s is not slot)

    def choose(day: dt.date, meal: str, exclude: Dish | None = None) -> Dish | None:
        same_day = [at.get((day, m)) for m in MEALS if m != meal]
        near = [at.get((day - ONE_DAY, meal)), at.get((day + ONE_DAY, meal)),
                at.get((day - ONE_DAY, "dinner")) if meal == "lunch" else None]
        options = [d for d in dishes if meal in d.meals and not (exclude and d.id == exclude.id)]
        return _pick(options, uses, rng, _ids(same_day), _ids(near))

    dish = choose(slot.day, slot.meal, exclude=slot.dish)
    if dish is None:
        return None
    new = cook(slot.day, slot.meal, dish)
    changed = [new]
    lunch = at.get((slot.day + ONE_DAY, "lunch"))
    if slot.meal == "dinner" and lunch and not lunch.cooked:
        at[(new.day, new.meal)] = new
        if new.multiplier >= 2:
            changed.append(leftovers_of(dish, lunch.day))
        elif lunch.leftovers and (own := choose(lunch.day, "lunch")):
            changed.append(cook(lunch.day, "lunch", own))
    return changed
