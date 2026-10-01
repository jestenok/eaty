"""Logic of the web app that doesn't need a database."""

import datetime as dt

import pytest

from app.clients.wolt_catalog import parse_item
from app.service import shopping_calculator as shopping
from app.service.orders import parse_time
from app.utils.matching import matches
from app.utils.units import format_amount, parse_amount
from config import AppConfig
from core.error import ConfigError
from data import recipes as recipes_data


@pytest.mark.parametrize(
    "text, expected",
    [
        ("500 г", (500, "g")),
        ("1 кг", (1000, "g")),
        ("1,5 кг", (1500, "g")),
        ("~1000 г", (1000, "g")),
        ("15 шт", (15, "pcs")),
        ("1 л", (1000, "ml")),
        ("Рис Сэвил пропаренный 800 г", (800, "g")),
        ("Кикнос помидоры нарезанные 400 гр", (400, "g")),
        ("Молоко 3,2% 1л", (1000, "ml")),
        ("Банан, 1 кг", (1000, "g")),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


def test_parse_amount_ignores_words_that_start_like_units():
    assert parse_amount("Литовский хлеб") is None
    assert parse_amount("2 головки чеснока") is None


@pytest.mark.parametrize("amount, unit, text", [(600, "g", "600 г"), (1200, "g", "1,2 кг"), (5, "pcs", "5 шт"), (400, "ml", "400 мл")])
def test_format_amount(amount, unit, text):
    assert format_amount(amount, unit) == text


def product(key="potato", unit="g"):
    return shopping.Product(key, key, unit, "wolt-market-batumi")


def test_preferred_offer_wins_over_cheaper():
    cheap = shopping.Offer("a", "wm", "Дешёвый", 100, 1000)
    preferred = shopping.Offer("b", "wm", "Любимый", 300, 1000, preferred=True)
    assert shopping.choose_offer([cheap, preferred]) is preferred


def test_cheapest_per_unit_without_preferred():
    small = shopping.Offer("a", "wm", "400 г", 400, 400)     # 1 tetri/g
    big = shopping.Offer("b", "wm", "1 кг", 800, 1000)       # 0.8 tetri/g
    assert shopping.choose_offer([small, big]) is big


def test_build_subtracts_pantry_and_rounds_packs_up():
    offers = {"potato": [shopping.Offer("p", "wm", "Картофель", 165, 1000, preferred=True)]}
    [line] = shopping.build({"potato": 1800}, {"potato": 300}, {"potato": product()}, offers)
    assert line.to_buy == 1500
    assert line.packs == 2
    assert line.cost == 330


def test_build_ignores_tiny_remainders():
    offers = {"garlic": [shopping.Offer("g", "wm", "Чеснок", 430, 250, preferred=True)]}
    [line] = shopping.build({"garlic": 260}, {}, {"garlic": product("garlic")}, offers)
    assert line.packs == 1  # 10 g over one pack is not worth a second one


def test_build_nothing_to_buy_when_pantry_is_enough():
    offers = {"eggs": [shopping.Offer("e", "wm", "Яйца 15 шт", 895, 15, preferred=True)]}
    [line] = shopping.build({"eggs": 10}, {"eggs": 15}, {"eggs": product("eggs", "pcs")}, offers)
    assert line.packs == 0 and line.cost == 0
    assert shopping.by_store([line]) == []


def test_by_store_groups_and_totals():
    offers = {
        "potato": [shopping.Offer("p", "wolt-market-batumi", "Картофель", 165, 1000, preferred=True)],
        "chicken_legs": [shopping.Offer("c", "red-market-meat-store", "Ножка", 2281, 1100, preferred=True, by_weight=True)],
    }
    products = {"potato": product(), "chicken_legs": shopping.Product("chicken_legs", "Окорочка", "g", "red-market-meat-store")}
    lines = shopping.build({"potato": 2000, "chicken_legs": 2000}, {}, products, offers)
    stores = {s.venue_slug: s.total for s in shopping.by_store(lines)}
    assert stores == {"wolt-market-batumi": 330, "red-market-meat-store": 2 * 2281}


def test_catalog_item_sold_by_weight():
    raw = {"id": "x", "name": "Куриная ножка", "price": 2074, "unit_info": None,
           "sell_by_weight_config": {"grams_per_step": 1100, "price_per_kg": 2074}}
    item = parse_item(raw)
    assert (item.price, item.pack_amount, item.weight_step_g) == (2281, 1100, 1100)


def test_catalog_item_pack_and_disabled():
    assert parse_item({"id": "r", "name": "Рис 800 г", "price": 480, "unit_info": "800 г"}).pack_amount == 800
    assert parse_item({"id": "d", "name": "Рис", "price": 480, "disabled_info": {"x": 1}}) is None


@pytest.mark.parametrize("product_key, name, expected", [
    ("eggs", "Яйца кумысные, картонный рынок, I категория, 15 шт.", True),
    ("eggs", "Перепелиные яйца", False),
    ("cheese", "Сыр Sanebo заводской 250г (в)", True),
    ("cheese", "Плавленый сыр Mlekovita слои чеддер 130 г", False),
    ("potato", "Картофель (ц), ~1000 г", True),
    ("potato", "Сладкий картофель, ~500 г", False),
    ("chicken_legs", "Куриная ножка", True),
    ("chicken_legs", "Баркал копченой курицы", False),
    ("tomatoes_canned", "Кикнос помидоры нарезанные 400 гр", True),
    ("tomatoes_canned", "Томатная паста 70 г", False),
    ("rice", "Рис Сэвил пропаренный 800 г", True),
    ("rice", "Рисовые хлопья", False),
])
def test_product_patterns(product_key, name, expected):
    p = next(p for p in recipes_data.PRODUCTS if p["key"] == product_key)
    assert matches(name, p["match"], p["exclude"]) is expected


def test_preferred_items_match_their_own_product():
    for p in recipes_data.PRODUCTS:
        assert matches(p["preferred"][1], p["match"], p["exclude"]), p["key"]


def test_recipes_are_consistent():
    keys = {p["key"]: p["base_unit"] for p in recipes_data.PRODUCTS}
    slugs = {r["slug"] for r in recipes_data.RECIPES}
    for r in recipes_data.RECIPES:
        assert r["steps"], r["slug"]
        for i in r["ingredients"]:
            if i["product_key"]:
                assert keys[i["product_key"]] == i["unit"], (r["slug"], i["name"])
                assert i["amount"] > 0
            else:
                assert i["text_amount"], (r["slug"], i["name"])
        for s in r["steps"]:
            assert s["timer_seconds"] is None or s["timer_seconds"] > 0
    for day in recipes_data.WEEK_TEMPLATE:
        assert set(day) == {"breakfast", "lunch", "dinner"}
        for slug, multiplier, note in day.values():
            assert slug in slugs or (slug is None and note)


def config_with(monkeypatch, **env):
    for key in ("DATABASE_URL", "POSTGRES_URI", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return AppConfig()


def test_database_url_from_sqlalchemy_style_uri(monkeypatch):
    url = config_with(monkeypatch, POSTGRES_URI="postgresql+asyncpg://u:p@host:30000", DB_NAME="eaty").DATABASE_URL
    assert url.render_as_string(hide_password=False) == "postgresql+asyncpg://u:p@host:30000/eaty"


def test_database_url_plain_postgres_gets_asyncpg_and_keeps_database(monkeypatch):
    url = config_with(monkeypatch, POSTGRES_URI="postgresql://u:p@host:5432/other").DATABASE_URL
    assert (url.drivername, url.database) == ("postgresql+asyncpg", "other")


def test_full_database_url_wins_and_keeps_explicit_async_driver(monkeypatch):
    url = config_with(monkeypatch, POSTGRES_URI="postgresql://u:p@host/x",
                      DATABASE_URL="postgresql+psycopg://u:p@localhost/eaty_test").DATABASE_URL
    assert (url.drivername, url.database) == ("postgresql+psycopg", "eaty_test")


def test_database_url_rejects_other_databases(monkeypatch):
    with pytest.raises(ConfigError):
        config_with(monkeypatch, DATABASE_URL="sqlite:///eaty.db").DATABASE_URL


def test_database_url_missing(monkeypatch):
    with pytest.raises(ConfigError):
        config_with(monkeypatch).DATABASE_URL


def test_without_env_the_service_listens_like_in_a_container(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    config = AppConfig()
    assert (config.HOST, config.RELOAD) == ("0.0.0.0", False)
    monkeypatch.setenv("ENV", "local")
    assert (AppConfig().HOST, AppConfig().RELOAD) == ("127.0.0.1", True)


@pytest.mark.parametrize("value, expected", [
    (1790848000000, dt.datetime(2026, 10, 1, 9, 46, 40, tzinfo=dt.timezone.utc)),
    ({"$date": 1790848000000}, dt.datetime(2026, 10, 1, 9, 46, 40, tzinfo=dt.timezone.utc)),
    ("2026-10-01T09:46:40Z", dt.datetime(2026, 10, 1, 9, 46, 40, tzinfo=dt.timezone.utc)),
    ("not a date", None),
    (None, None),
])
def test_order_time(value, expected):
    assert parse_time(value) == expected


def test_default_port_matches_the_cluster_chart(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    assert AppConfig().PORT == 8080
