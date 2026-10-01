"""Putting a week menu together and the order task, without a database."""

import datetime as dt
import json
import random
from pathlib import Path

import pytest

from app.schemas.shopping import ShoppingItemOut, ShoppingLineOut, ShoppingListOut, ShoppingStoreOut
from app.service import menu_builder as menu
from app.service.order_task import order_task, period

START = dt.date(2026, 10, 5)
BOOK = json.loads((Path(__file__).parents[1] / "src/migrations/data/recipe_book.json").read_text(encoding="utf-8"))


def dish(id, title, meals, batch=False, needs=None):
    return menu.Dish(id, title, frozenset(meals), batch, needs or {})


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


def test_the_recipe_book_makes_a_week():
    dishes = [dish(n, r["title"], r["meals"], bool(r.get("batch_note"))) for n, r in enumerate(BOOK["recipes"])]
    week = menu.build_week(dishes, START, random.Random(5))
    assert len(week) == 21 and all(s.dish or s.leftovers for s in week)
    assert len({s.dish.id for s in week if s.dish}) == len([s for s in week if s.dish])  # 82 recipes: no repeats


def test_cooked_meals_stay():
    cooked = menu.Slot(START, "breakfast", OATS, cooked=True)
    week = menu.build_week(DISHES, START, random.Random(6), days=2, cooked=[cooked])
    assert week[0] is cooked
    assert at(week, 1, "breakfast").dish != OATS     # it counts as eaten: the next breakfast is another


# ---------- from what's at home ----------

H_OATS = dish(11, "Овсянка", ["breakfast"], needs={"oats": 140, "milk": 400})
H_EGGS = dish(12, "Яичница", ["breakfast"], needs={"eggs": 5, "bread": 150})
H_LEGS = dish(13, "Окорочка", ["dinner"], True, needs={"chicken_legs": 650, "potato": 600})
H_SHAKSHUKA = dish(14, "Шакшука", ["lunch", "dinner"], needs={"eggs": 5, "tomatoes": 400})
H_SOUP = dish(15, "Суп", ["lunch"], needs={"chicken_legs": 400, "potato": 250})
HOME_DISHES = [H_OATS, H_EGGS, H_LEGS, H_SHAKSHUKA, H_SOUP]


def used(week):
    total = {}
    for s in week:
        if s.dish and not s.cooked:
            for key, need in s.dish.needs.items():
                total[key] = total.get(key, 0) + need * s.multiplier
    return total


@pytest.mark.parametrize("seed", range(20))
def test_from_home_only_what_there_is_enough_for(seed):
    have = {"oats": 500, "milk": 1000, "eggs": 10, "bread": 300, "chicken_legs": 1300, "potato": 1200, "tomatoes": 400}
    week = menu.build_week(HOME_DISHES, START, random.Random(seed), stock=menu.Stock(have))
    # every dish takes its products out as it goes in: all together never take more than is at home
    assert all(need <= have[key] for key, need in used(week).items()), used(week)
    assert len(week) < 21                              # the rest of the week there is nothing for
    assert sum(s.dish == H_OATS for s in week) == 2    # milk for two
    for s in week:
        if s.dish == H_LEGS and s.multiplier == 2:     # enough legs for x2: tomorrow's lunch is the other half
            assert any(l.leftovers and l.day == s.day + dt.timedelta(days=1) for l in week)


def test_from_home_a_batch_dinner_once_if_enough_for_one_cooking():
    week = menu.build_week([H_LEGS], START, random.Random(1), days=2,
                           stock=menu.Stock({"chicken_legs": 700, "potato": 700}))
    [dinner] = week                                    # and no leftovers for tomorrow's lunch
    assert (dinner.dish, dinner.multiplier, dinner.note) == (H_LEGS, 1, "")


def test_from_home_counts_roughly_and_skips_what_is_not_at_home():
    stock = menu.Stock({"eggs": 5, "bread": 135, "milk": -200})
    assert stock.fits(H_EGGS)                          # 135 g of bread for 150 g will do
    assert stock.short(H_OATS) == ["oats", "milk"]
    assert menu.build_week([H_OATS], START, random.Random(1), stock=stock) == []


@pytest.mark.parametrize("seed", range(10))
def test_swap_from_home_takes_what_is_left_then_one_to_buy(seed):
    toast = dish(16, "Тосты", ["breakfast"], needs={"bread": 150, "milk": 100})
    week = menu.build_week([H_OATS], START, random.Random(seed), days=2, stock=menu.Stock({"oats": 280, "milk": 800}))
    assert [s.dish for s in week] == [H_OATS, H_OATS]
    # the other day's oats go first, and what's left makes toast; there are no eggs
    have = {"oats": 280, "milk": 800, "bread": 150}
    [new] = menu.swap(week, week[0], [H_OATS, H_EGGS, toast], random.Random(seed), menu.Stock(have))
    assert new.dish == toast
    # no bread either: one to buy, with the fewest products to buy (eggs are at home)
    [new] = menu.swap(week, week[0], [H_OATS, H_EGGS, toast], random.Random(seed), menu.Stock({"eggs": 5}))
    assert new.dish == H_EGGS
    # an empty meal gets a dish too, one there is enough for first
    empty = menu.Slot(START, "lunch", None)
    [lunch] = menu.swap(week, empty, [H_SHAKSHUKA, H_SOUP], random.Random(seed), menu.Stock({"eggs": 5, "tomatoes": 400}))
    assert lunch.dish == H_SHAKSHUKA
    # but not the breakfast once more: a dish eaten that day loses even to one to buy
    omelette = dish(17, "Омлет", ["breakfast", "lunch"], needs={"eggs": 5})
    day = [menu.Slot(START, "breakfast", omelette)]
    [lunch] = menu.swap(day, empty, [omelette, H_SOUP], random.Random(seed), menu.Stock({"eggs": 10}))
    assert lunch.dish == H_SOUP


def test_shortages_go_in_the_order_meals_are_eaten():
    week = [menu.Slot(START, "breakfast", H_EGGS, cooked=True),        # cooked: taken out already
            menu.Slot(START, "dinner", H_SHAKSHUKA),
            menu.Slot(START + dt.timedelta(days=1), "breakfast", H_EGGS),
            menu.Slot(START + dt.timedelta(days=1), "lunch", None, note="Шакшука со вчера")]
    short = menu.shortages(week, menu.Stock({"eggs": 7, "bread": 200, "tomatoes": 400}))
    assert short == {(START + dt.timedelta(days=1), "breakfast"): ["eggs"]}


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
