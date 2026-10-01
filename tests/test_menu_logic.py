"""Putting a week menu together and the order task, without a database."""

import datetime as dt
import random

import pytest

from app.schemas.shopping import ShoppingItemOut, ShoppingLineOut, ShoppingListOut, ShoppingStoreOut
from app.service import menu_builder as menu
from app.service.order_task import order_task, period
from data import recipes as recipes_data

START = dt.date(2026, 10, 5)


def dish(id, title, meals, batch=False):
    return menu.Dish(id, title, frozenset(meals), batch)


OATS, EGGS, OMELETTE = dish(1, "Овсянка", ["breakfast"]), dish(2, "Яичница", ["breakfast"]), dish(3, "Омлет", ["breakfast", "lunch"])
LEGS, PASTA, PLOV = dish(4, "Окорочка", ["dinner"], True), dish(5, "Болоньезе", ["dinner"], True), dish(6, "Плов", ["dinner"], True)
SHAKSHUKA = dish(7, "Шакшука", ["lunch", "dinner"])
DISHES = [OATS, EGGS, OMELETTE, LEGS, PASTA, PLOV, SHAKSHUKA]


def at(week, offset, meal):
    return next(s for s in week if (s.day, s.meal) == (START + dt.timedelta(days=offset), meal))


@pytest.mark.parametrize("seed", range(20))
def test_week_follows_the_rules(seed):
    week = menu.build_week(DISHES, START, random.Random(seed))
    assert len(week) == 21
    for offset in range(7):
        breakfast, lunch, dinner = (at(week, offset, m) for m in menu.MEALS)
        assert "breakfast" in breakfast.dish.meals and "dinner" in dinner.dish.meals
        # a batch dinner is cooked x2 and makes tomorrow's lunch
        assert (dinner.multiplier, dinner.note) == ((2, menu.BATCH_NOTE) if dinner.dish.batch else (1, ""))
        yesterday = at(week, offset - 1, "dinner") if offset else None
        if yesterday and yesterday.dish.batch:
            assert lunch.leftovers and lunch.note == f"{yesterday.dish.title} со вчера" and lunch.multiplier == 1
        else:
            assert "lunch" in lunch.dish.meals
        if yesterday:
            assert dinner.dish != yesterday.dish, "the same dinner two days running"
        eaten = [s.dish.id for s in (breakfast, lunch, dinner) if s.dish]
        assert len(eaten) == len(set(eaten)), "one dish twice a day"
    # dishes rotate: 4 dinners over 7 days, none more than twice
    dinners = [at(week, offset, "dinner").dish.id for offset in range(7)]
    assert set(dinners) == {LEGS.id, PASTA.id, PLOV.id, SHAKSHUKA.id}
    assert max(dinners.count(d) for d in set(dinners)) == 2


def test_first_lunch_is_the_leftovers_of_the_eve():
    eve = menu.Slot(START - dt.timedelta(days=1), "dinner", PLOV, 2, menu.BATCH_NOTE)
    week = menu.build_week(DISHES, START, random.Random(1), before=eve)
    assert at(week, 0, "lunch").note == "Плов со вчера"
    assert at(week, 0, "dinner").dish != PLOV
    single = menu.Slot(START - dt.timedelta(days=1), "dinner", SHAKSHUKA, 1)
    assert at(menu.build_week(DISHES, START, random.Random(1), before=single), 0, "lunch").dish == OMELETTE


def test_meals_without_recipes_are_left_out():
    week = menu.build_week([LEGS, PASTA], START, random.Random(1), days=2)
    assert [(s.meal, s.dish and s.dish.title) for s in week] == [
        ("dinner", week[0].dish.title), ("lunch", None), ("dinner", week[2].dish.title)]


def test_swap_a_breakfast():
    week = menu.build_week(DISHES, START, random.Random(3))
    old = at(week, 2, "breakfast")
    [new] = menu.swap(week, old, DISHES, random.Random(3))
    assert (new.day, new.meal) == (old.day, "breakfast")
    assert new.dish != old.dish and "breakfast" in new.dish.meals


def test_swap_a_dinner_decides_tomorrows_lunch():
    week = menu.build_week([OATS, EGGS, OMELETTE, LEGS, SHAKSHUKA], START, random.Random(2))
    legs = next(s for s in week if s.meal == "dinner" and s.dish == LEGS and s.day < START + dt.timedelta(days=6))
    # legs x2 -> shakshuka x1: tomorrow's lunch is no longer leftovers but a dish of its own
    dinner, lunch = menu.swap(week, legs, [OATS, EGGS, OMELETTE, LEGS, SHAKSHUKA], random.Random(2))
    assert (dinner.dish, dinner.multiplier, dinner.note) == (SHAKSHUKA, 1, "")
    assert lunch.day == legs.day + dt.timedelta(days=1) and lunch.dish == OMELETTE
    # and back: shakshuka x1 -> legs x2, tomorrow's lunch is the leftovers again
    week = [dinner if (s.day, s.meal) == (dinner.day, dinner.meal) else lunch if (s.day, s.meal) == (lunch.day, lunch.meal)
            else s for s in week]
    again, leftovers = menu.swap(week, dinner, [OMELETTE, LEGS, SHAKSHUKA], random.Random(2))
    assert (again.dish, again.multiplier) == (LEGS, 2)
    assert leftovers.note == "Окорочка со вчера"


def test_swap_keeps_a_cooked_lunch_and_the_last_day():
    week = menu.build_week(DISHES, START, random.Random(4))
    tuesday_lunch = at(week, 1, "lunch")
    week = [s if s is not tuesday_lunch else menu.Slot(s.day, s.meal, s.dish, s.multiplier, s.note, cooked=True)
            for s in week]
    assert len(menu.swap(week, at(week, 0, "dinner"), DISHES, random.Random(4))) == 1
    assert len(menu.swap(week, at(week, 6, "dinner"), DISHES, random.Random(4))) == 1  # tomorrow is not this menu


def test_nothing_to_swap_with():
    week = menu.build_week([OATS, LEGS], START, random.Random(1), days=1)
    assert menu.swap(week, at(week, 0, "breakfast"), [OATS, LEGS], random.Random(1)) is None


def test_builtin_recipes_make_a_week():
    dishes = [dish(n, r["title"], r["meals"], bool(r.get("batch_note"))) for n, r in enumerate(recipes_data.RECIPES)]
    week = menu.build_week(dishes, START, random.Random(5))
    assert len(week) == 21 and all(s.dish or s.leftovers for s in week)


def test_period():
    assert period(dt.date(2026, 10, 2), dt.date(2026, 10, 8)) == "2–8 октября"
    assert period(dt.date(2026, 9, 29), dt.date(2026, 10, 5)) == "29 сентября – 5 октября"


def line(product, packs, cost, item=None, need="1 кг", to_buy="1 кг"):
    return ShoppingLineOut(product_key=product, product=product, need=need, have="", to_buy=to_buy, packs=packs,
                           cost=cost, item=item)


def test_order_task_lists_stores_items_and_rules():
    legs = ShoppingItemOut(id="c7", name="Куриная ножка", price=2281, pack="1,1 кг", by_weight=True,
                           url="https://wolt.com/ru/geo/batumi/venue/red/itemid-c7")
    rice = ShoppingItemOut(id="r1", name="Рис 800 г", price=480, pack="800 г", by_weight=False,
                           url="https://wolt.com/ru/geo/batumi/venue/wm/itemid-r1")
    shopping = ShoppingListOut(
        start=START, days=7, prices_updated_at=None, total=2 * 2281 + 480, enough=[],
        stores=[ShoppingStoreOut(venue_slug="red", name="Red Market (мясо)", url="https://wolt.com/ru/geo/batumi/venue/red",
                                 total=2 * 2281, lines=[line("Окорочка", 2, 2 * 2281, legs, to_buy="2,2 кг")]),
                ShoppingStoreOut(venue_slug="wm", name="Wolt Market Batumi", url="https://wolt.com/ru/geo/batumi/venue/wm",
                                 total=480, lines=[line("Рис", 1, 480, rice, to_buy="400 г")])],
        not_found=[line("Хлеб", 0, 0, to_buy="600 г")])
    task = order_task(START, START + dt.timedelta(days=6), shopping)
    assert task.startswith("Закажи в Wolt продукты для меню eaty на 5–11 октября.")
    assert "Магазинов: 2, каждый — отдельный заказ. Товары на сумму около 50,42 ₾" in task
    assert "1. Red Market (мясо) — https://wolt.com/ru/geo/batumi/venue/red (≈ 45,62 ₾)" in task
    assert ("   - 2 × Куриная ножка (на развес, шаг 1,1 кг, 22,81 ₾ за шаг) — для «Окорочка», нужно 2,2 кг"
            " — https://wolt.com/ru/geo/batumi/venue/red/itemid-c7") in task
    assert "   - 1 × Рис 800 г (800 г, 4,80 ₾) — для «Рис», нужно 400 г" in task
    assert "   - Хлеб: нужно 600 г" in task
    assert "жди моего «да»" in task


def test_order_task_when_everything_is_at_home():
    empty = ShoppingListOut(start=START, days=7, prices_updated_at=None, stores=[], enough=[], not_found=[], total=0)
    assert order_task(START, START, empty).endswith("Докупать ничего не нужно: всё уже дома.")
