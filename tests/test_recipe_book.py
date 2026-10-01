"""The recipe book a migration loads into the database (src/migrations/data/recipe_book.json).
Checked without a database: everything in it must pass the API's own validation."""

import json
from pathlib import Path

import pytest

from app.schemas.product import ProductIn
from app.schemas.recipe import RecipeIn
from app.utils.matching import matches
from app.utils.units import parse_amount

BOOK = json.loads((Path(__file__).parents[1] / "src/migrations/data/recipe_book.json").read_text(encoding="utf-8"))
PRODUCTS = {p["key"]: p for p in BOOK["products"]}
RECIPES = BOOK["recipes"]


def products_matching(name: str) -> list[str]:
    return [p["key"] for p in BOOK["products"] if matches(name, p["match_re"], p["exclude_re"])]


def test_the_book_is_big():
    assert len(RECIPES) >= 80
    assert {r["category"] for r in RECIPES} == {"breakfast", "soup", "main", "salad", "snack", "dessert"}


def test_products_pass_the_api_validation():
    assert len(PRODUCTS) == len(BOOK["products"])
    for p in BOOK["products"]:
        ProductIn.model_validate(p)


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r["slug"])
def test_recipe_passes_the_api_validation(recipe):
    RecipeIn.model_validate(recipe)
    for i in recipe["ingredients"]:
        if "product_key" in i:
            assert PRODUCTS[i["product_key"]]["base_unit"] == i["unit"], i["name"]
    if recipe["appliance"] != "none":
        assert any(s.get("timer_seconds") for s in recipe["steps"]), "a cooked dish needs at least one timer"


def test_slugs_and_titles_are_unique():
    assert len({r["slug"] for r in RECIPES}) == len({r["title"] for r in RECIPES}) == len(RECIPES)


def test_every_product_is_used():
    used = {i["product_key"] for r in RECIPES for i in r["ingredients"] if "product_key" in i}
    assert set(PRODUCTS) - used == set()


def test_week_template_points_at_recipes():
    slugs = {r["slug"] for r in RECIPES}
    assert {(w["day_offset"], w["meal"]) for w in BOOK["week_template"]} == {
        (d, m) for d in range(7) for m in ("breakfast", "lunch", "dinner")}
    for w in BOOK["week_template"]:
        assert w["recipe_slug"] in slugs or (w["recipe_slug"] is None and w["note"])


def test_each_product_name_is_its_own_and_only_its_own():
    """An order line goes to the first product whose pattern fits, so patterns must not overlap."""
    for p in BOOK["products"]:
        assert products_matching(p["name"]) == [p["key"]], p["name"]


def test_preferred_items_match_their_own_product():
    for item in BOOK["wolt_items"]:
        assert products_matching(item["name"]) == [item["product_key"]], item["name"]


@pytest.mark.parametrize("name, product_key", [
    ("Яйца кумысные, картонный рынок, I категория, 15 шт.", "eggs"),
    ("Перепелиные яйца", None),
    ("Сыр Sanebo заводской 250г (в)", "cheese"),
    ("Плавленый сыр Mlekovita слои чеддер 130 г", None),
    ("Сыр сулугуни 300 г", "suluguni"),
    ("Сыр Фета 200 г", "feta"),
    ("Творожный сыр 150 г", None),
    ("Творог 9% 200 г", "tvorog"),
    ("Картофель (ц), ~1000 г", "potato"),
    ("Сладкий картофель, ~500 г", None),
    ("Куриная ножка", "chicken_legs"),
    ("Баркал копченой курицы", None),
    ("Филе куриной грудки", "chicken_breast"),
    ("Куриное филе варёное", None),
    ("Куриная печень", "chicken_liver"),
    ("Печенье Юбилейное", None),
    ("Фарш говяжий 500 г", "beef_mince"),
    ("Говядина вырезка", "beef"),
    ("Говядина тушёная", None),
    ("Свиная шея", "pork"),
    ("Рёбра свиные", "pork_ribs"),
    ("Бекон сырокопчёный 150 г", "bacon"),
    ("Филе трески", "white_fish"),
    ("Печень трески", None),
    ("Кикнос помидоры нарезанные 400 гр", "tomatoes_canned"),
    ("Томатная паста 70 г", None),
    ("Помидоры черри 250 г", "tomato"),
    ("Огурцы 1 кг", "cucumber"),
    ("Огурцы маринованные 680 г", "pickles"),
    ("Огурцы солёные", "pickles"),
    ("Лук Имери белый 500г (c)", "onion"),
    ("Лук зелёный 50 г", "green_onion"),
    ("Перец болгарский красный 500 г", "bell_pepper"),
    ("Перец красный молотый", None),
    ("Перец чёрный горошек", None),
    ("Горошек зелёный 400 г", "peas"),
    ("Капуста белокочанная ~1500 г", "cabbage"),
    ("Капуста цветная", None),
    ("Икра кабачковая", None),
    ("Шампиньоны маринованные", None),
    ("Лимонный сок", None),
    ("Мёд гречишный 250 г", None),
    ("Крупа гречневая ядрица 900 г", "buckwheat"),
    ("Лапша яичная 250 г", "noodles"),
    ("Лапша быстрого приготовления", None),
    ("Рис Сэвил пропаренный 800 г", "rice"),
    ("Рисовые хлопья", None),
    ("Фасоль красная в собственном соку 400 г", None),
    ("Тортилья пшеничная 6 шт", "lavash"),
    ("Сливки 20% 200 мл", "cream"),
    ("Масло сливочное 82,5% 180 г", "butter"),
    ("Чипсы Lay's сметана и лук", None),
    ("Салат Айсберг", "lettuce"),
    ("Салат Цезарь с курицей", None),
])
def test_order_lines_go_to_the_right_product(name, product_key):
    assert products_matching(name) == ([product_key] if product_key else [])


# A real order from Wolt Market Batumi: the order page shows the store's Georgian item names
# even on wolt.com/ru, and these are what the extension sends.
@pytest.mark.parametrize("name, product_key, amount", [
    ("მილა რძე 3.2% 1ლ", "milk", (1000, "ml")),
    ("კუმისი კვერცხი მუყაოს მარკეტი I კატეგორია 15ც", "eggs", (15, "pcs")),
    ("სანებო ქარხნული ყველი 250გრ (ქ)", "cheese", (250, "g")),
    ("იმერი თეთრი ხახვი 500გრ (ქ)", "onion", (500, "g")),
    ("იმერი სტაფილო 500გრ (ქ)", "carrot", (500, "g")),
    ("იმერი ნიორი 250გრ (ქ)", "garlic", (250, "g")),
    ("Arrighi მაკარონი სპაგეტი 500გრ", "pasta", (500, "g")),
    ("სავილე ბრინჯი ორთქლში გატარებული 800გრ", "rice", (800, "g")),
    ("კიკნოსი დაჭრილი პომიდორი 400გრ", "tomatoes_canned", (400, "g")),
    ("იარმარკა შვრიის ბურღული 600გრ", "oats", (600, "g")),
    ("ლიტვური საცხობი სენდვიჩ ტოსტი 600გრ", "bread", (600, "g")),
])
def test_georgian_order_names_find_their_product(name, product_key, amount):
    assert products_matching(name) == [product_key]
    assert parse_amount(name) == amount


@pytest.mark.parametrize("name", [
    "შოკოლადის რძე 200მლ",
    "დნობილი ყველი 100გრ",
    "ბრინჯის რძე 1ლ",
    "სულგუნი ყველი 300გრ",      # suluguni and feta have products of their own
    "ფეტა ყველი 200გრ",
])
def test_georgian_names_that_are_not_the_basic_product(name):
    assert "milk" not in products_matching(name) and "cheese" not in products_matching(name)
    assert "rice" not in products_matching(name)
