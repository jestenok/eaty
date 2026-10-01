"""The web app against a real Postgres: migrations, seed data, the API and the unit of work.
Needs TEST_DATABASE_URL (see conftest.py); skipped otherwise."""

import datetime as dt
import time

import pytest

TODAY = dt.date.today().isoformat()
NOW_MS = int(time.time() * 1000)
DAY_MS = 24 * 3600 * 1000


async def pantry(client) -> dict[str, float]:
    return {p["key"]: p["have"] for p in (await client.get("/pantry")).json()}


async def test_migrations_and_seed_give_a_planned_day_with_timers(client):
    plan = (await client.get("/plan", params={"start": TODAY, "days": 1})).json()
    assert [p["meal"] for p in plan] == ["breakfast", "lunch", "dinner"]
    recipe = (await client.get(f"/recipes/{plan[2]['recipe_id']}")).json()
    assert recipe["title"] == "Окорочка с картошкой в аэрогриле"
    assert sum(s["timer_seconds"] or 0 for s in recipe["steps"]) == (15 + 17 + 5) * 60


async def test_order_fills_pantry_and_cooking_uses_it(client):
    order = {"id": "o1", "venue_name": "Wolt Market Batumi", "ordered_at": NOW_MS, "items": [
        {"id": "66a0dd8b9dfb545d3cc3f96f", "name": "Яйца 15 шт.", "count": 1},
        {"id": None, "name": "Картофель (ц), ~1000 г", "count": 2},
        {"id": None, "name": "Шоколад Alpen Gold", "count": 1},
    ]}
    assert (await client.post("/wolt-orders", json={"orders": [order]})).json() == {
        "orders": 1, "pantry_items": 2, "skipped_restaurants": 0, "skipped_unknown": 0, "skipped_old": 0}
    await client.post("/wolt-orders", json={"orders": [order]})  # the same order again must not double up
    have = await pantry(client)
    assert have["eggs"] == 15 and have["potato"] == 2000

    [saved] = (await client.get("/wolt-orders")).json()
    assert [i["product_key"] for i in saved["items"]] == ["eggs", "potato", None]

    omelette = next(r["id"] for r in (await client.get("/recipes")).json() if r["slug"] == "omelette")
    await client.put(f"/plan/{TODAY}/lunch", json={"recipe_id": omelette, "multiplier": 1})
    [_, lunch, _] = (await client.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": True})).json()
    assert lunch["cooked_at"] is not None
    assert (await pantry(client))["eggs"] == 10
    await client.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": False})
    assert (await pantry(client))["eggs"] == 15


async def test_an_order_from_the_page_and_from_wolt_data_counts_once(client):
    # Read off wolt.com/ru/me/order-history/<id>: the store's Georgian names, no item ids.
    from_page = {"id": "6abe16f7eccfcf01484147c4", "venue_name": "Wolt Market Batumi", "items": [
        {"name": "იმერი სტაფილო 500გრ (ქ)", "count": 2, "price": 660},
        {"name": "მილა რძე 3.2% 1ლ", "count": 1, "price": 595},
        {"name": "კიკნოსი დაჭრილი პომიდორი 400გრ", "count": 2, "price": 900},
    ]}
    # The same order from Wolt's own data: item ids, another order of items.
    from_data = {"id": "6abe16f7eccfcf01484147c4", "venue_name": "Wolt Market Batumi", "items": [
        {"id": "67b11a65b43072db0d097720", "name": "მილა რძე 3.2% 1ლ", "count": 1},
        {"id": "880f7bdbb1e9f4ce9edd2863", "name": "კიკნოსი დაჭრილი პომიდორი 400გრ", "count": 2},
        {"id": "66d9ac1d5116df1f4f1ceec9", "name": "იმერი სტაფილო 500გრ (ქ)", "count": 2},
    ]}
    nothing_skipped = {"skipped_restaurants": 0, "skipped_unknown": 0, "skipped_old": 0}
    assert (await client.post("/wolt-orders", json={"orders": [from_page]})).json() == {
        "orders": 1, "pantry_items": 3, **nothing_skipped}
    assert (await client.post("/wolt-orders", json={"orders": [from_data]})).json() == {
        "orders": 1, "pantry_items": 0, **nothing_skipped}
    have = await pantry(client)
    assert (have["carrot"], have["milk"], have["tomatoes_canned"]) == (1000, 1000, 800)


async def test_write_off_of_a_cooked_meal_can_be_edited(client):
    for key, amount in {"eggs": 15, "milk": 1000, "cheese": 250}.items():
        await client.put(f"/pantry/{key}", json={"amount": amount})
    omelette = next(r["id"] for r in (await client.get("/recipes")).json() if r["slug"] == "omelette")
    await client.put(f"/plan/{TODAY}/lunch", json={"recipe_id": omelette, "multiplier": 1})
    used_url = f"/plan/{TODAY}/lunch/used"

    assert (await client.get(used_url)).json() == []
    assert (await client.put(used_url, json={"amounts": {"eggs": 4}})).status_code == 409  # not cooked yet

    await client.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": True})
    used = (await client.get(used_url)).json()
    assert {u["key"]: u["amount"] for u in used} == {"eggs": 5, "milk": 50, "cheese": 50, "bread": 100}
    assert next(u for u in used if u["key"] == "eggs")["amount_text"] == "5 шт"

    # took 4 eggs, more milk, no cheese, and some potatoes the recipe doesn't have
    edited = (await client.put(used_url, json={"amounts": {"eggs": 4, "milk": 120, "cheese": 0, "potato": 300}})).json()
    assert {u["key"]: u["amount"] for u in edited} == {"eggs": 4, "milk": 120, "potato": 300}
    have = await pantry(client)
    assert (have["eggs"], have["milk"], have["cheese"], have["bread"]) == (11, 880, 250, 0)

    assert (await client.put(used_url, json={"amounts": {"nope": 1}})).status_code == 404
    assert (await client.put(used_url, json={"amounts": {"eggs": -1}})).status_code == 422
    assert (await pantry(client))["eggs"] == 11

    await client.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": False})  # undo gives back what was edited
    have = await pantry(client)
    assert (have["eggs"], have["milk"], have["potato"]) == (15, 1000, 0)


async def test_pantry_correction(client):
    assert (await client.put("/pantry/milk", json={"amount": 700})).json()["have"] == 700
    assert (await pantry(client))["milk"] == 700
    assert (await client.put("/pantry/nope", json={"amount": 1})).status_code == 404


async def test_shopping_list_prices_in_two_stores(client):
    data = (await client.get("/shopping", params={"start": TODAY, "days": 7})).json()
    assert {s["venue_slug"] for s in data["stores"]} == {"wolt-market-batumi", "red-market-meat-store"}
    assert data["total"] == sum(s["total"] for s in data["stores"]) > 0
    legs = next(l for s in data["stores"] for l in s["lines"] if l["product_key"] == "chicken_legs")
    assert legs["item"]["by_weight"] and legs["item"]["url"].endswith("itemid-c71af1cad259d733a9205145")


async def test_bad_input_is_rejected(client):
    assert (await client.put("/plan/2026-10-01/supper", json={})).status_code == 422
    assert (await client.put("/plan/2026-10-01/lunch", json={"recipe_id": 999})).status_code == 404
    assert (await client.post("/wolt-orders", json={"orders": [{"id": "x", "items": []}]})).status_code == 422


async def test_a_failing_request_leaves_nothing_behind(app, client):
    """The unit of work belongs to the request: services only change the session, so when
    the handler fails after a write, the write is rolled back."""
    from api.dependencies import PantryServiceDep

    @app.post("/api/v1/_test/fail-after-write")
    async def fail_after_write(service: PantryServiceDep):
        await service.set_level("milk", 500)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await client.post("/_test/fail-after-write")
    assert (await pantry(client))["milk"] == 0


async def test_health(client):
    assert (await client.get("/health")).json() == {"ok": True}


async def test_sync_log_keeps_what_the_extension_saw(client):
    log = {"source": "button", "orders_found": 0, "error": "не разобрали",
           "details": {"order_rows": 12, "responses": [{"path": "/v1/x", "keys": ["a"], "orders": 0}]}}
    saved = (await client.post("/wolt-orders/sync-log", json=log)).json()
    assert saved["id"] and saved["created_at"] and saved["details"]["order_rows"] == 12
    [latest] = (await client.get("/wolt-orders/sync-log", params={"limit": 1})).json()
    assert latest["error"] == "не разобрали"


async def test_only_recent_store_orders_are_imported(client):
    item = {"id": None, "name": "Банан, 1 кг", "count": 1}
    orders = [
        {"id": "store", "venue_name": "Wolt Market Batumi", "ordered_at": NOW_MS, "items": [item]},
        {"id": "burger", "venue_name": "Burger King Batumi", "venue_url": "https://wolt.com/ru/geo/batumi/restaurant/bk",
         "ordered_at": NOW_MS, "items": [{"id": None, "name": "Воппер", "count": 1}]},
        {"id": "cafe", "venue_name": "Aromi Italiani", "ordered_at": NOW_MS, "items": [item]},
        {"id": "old", "venue_name": "Wolt Market Batumi", "ordered_at": NOW_MS - 10 * DAY_MS, "items": [item]},
    ]
    result = (await client.post("/wolt-orders", json={"orders": orders})).json()
    assert result == {"orders": 1, "pantry_items": 1, "skipped_restaurants": 1, "skipped_unknown": 1, "skipped_old": 1}
    assert [o["id"] for o in (await client.get("/wolt-orders")).json()] == ["store"]
    assert (await pantry(client))["banana"] == 1000


SOUP = {
    "slug": "test-soup", "title": "Тестовый суп", "category": "soup", "appliance": "stove",
    "ingredients": [
        {"name": "Картофель", "product_key": "potato", "amount": 300, "unit": "g"},
        {"name": "Соль", "text_amount": "по вкусу"},
    ],
    "steps": [
        {"text": "Нарезать."},
        {"text": "Варить.", "timer_seconds": 900, "heat": "средний огонь"},
    ],
}


async def test_recipe_book_is_in_the_database(client):
    recipes = (await client.get("/recipes")).json()
    assert len(recipes) >= 80
    assert {r["category"] for r in recipes} == {"breakfast", "soup", "main", "salad", "snack", "dessert"}
    khinkali = next(r for r in recipes if r["slug"] == "khinkali")
    steps = (await client.get(f"/recipes/{khinkali['id']}")).json()["steps"]
    assert [s["timer_seconds"] for s in steps if s["timer_seconds"]] == [30 * 60, 12 * 60]


async def test_recipes_are_added_edited_and_deleted(client):
    created = await client.post("/recipes", json=SOUP)
    assert created.status_code == 201
    soup = created.json()
    assert (soup["portions"], soup["category"]) == (2, "soup")
    assert [s["timer_seconds"] for s in soup["steps"]] == [None, 900]
    assert soup["ingredients"][0]["have"] is None and soup["ingredients"][1]["product_key"] is None

    assert (await client.post("/recipes", json=SOUP)).status_code == 409
    unknown = {**SOUP, "slug": "x", "ingredients": [{"name": "Тархун", "product_key": "tarragon", "amount": 5, "unit": "g"}]}
    assert (await client.post("/recipes", json=unknown)).status_code == 404
    wrong_unit = {**SOUP, "slug": "x", "ingredients": [{"name": "Картофель", "product_key": "potato", "amount": 3, "unit": "pcs"}]}
    assert (await client.post("/recipes", json=wrong_unit)).status_code == 400
    no_amount = {**SOUP, "slug": "x", "ingredients": [{"name": "Картофель", "product_key": "potato"}]}
    assert (await client.post("/recipes", json=no_amount)).status_code == 422

    # GET -> edit -> PUT: the output shape is accepted as input
    soup["title"] = "Суп с луком"
    soup["ingredients"].append({"name": "Лук", "product_key": "onion", "amount": 80, "unit": "g", "text_amount": "", "note": ""})
    soup["steps"] = soup["steps"][1:]
    updated = (await client.put(f"/recipes/{soup['id']}", json=soup)).json()
    assert updated["title"] == "Суп с луком" and updated["id"] == soup["id"]
    assert [i["name"] for i in updated["ingredients"]] == ["Картофель", "Соль", "Лук"]
    assert [(s["position"], s["text"]) for s in updated["steps"]] == [(0, "Варить.")]
    taken = {**SOUP, "slug": "khinkali"}
    assert (await client.put(f"/recipes/{soup['id']}", json=taken)).status_code == 409

    await client.put(f"/plan/{TODAY}/lunch", json={"recipe_id": soup["id"], "multiplier": 1})
    assert (await client.delete(f"/recipes/{soup['id']}")).status_code == 204
    assert (await client.get(f"/recipes/{soup['id']}")).status_code == 404
    [_, lunch, _] = (await client.get("/plan", params={"start": TODAY, "days": 1})).json()
    assert lunch["recipe_id"] is None
    assert (await client.delete(f"/recipes/{soup['id']}")).status_code == 404


async def test_products_are_added_and_used_in_recipes(client):
    tarragon = {"name": "Тархун", "base_unit": "g", "venue_slug": "wolt-market-batumi", "search_q": "тархун",
                "match_re": "тархун|эстрагон", "exclude_re": "лимонад|напит"}
    assert (await client.put("/products/tarragon", json=tarragon)).json()["key"] == "tarragon"
    assert "tarragon" in {p["key"] for p in (await client.get("/products")).json()}
    assert "tarragon" in await pantry(client)

    recipe = {**SOUP, "slug": "chakapuli", "ingredients": [{"name": "Тархун", "product_key": "tarragon", "amount": 40, "unit": "g"}]}
    assert (await client.post("/recipes", json=recipe)).status_code == 201

    assert (await client.put("/products/tarragon", json={**tarragon, "base_unit": "pcs"})).status_code == 409
    assert (await client.put("/products/tarragon", json={**tarragon, "match_re": "(тархун"})).status_code == 422
    assert (await client.put("/products/Bad Key", json=tarragon)).status_code == 422


async def test_fill_week_uses_the_template_from_the_database(client):
    start = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    await client.put(f"/plan/{start}/breakfast", json={"recipe_id": None, "note": "в гостях"})
    week = (await client.post("/plan/week", json={"start": start})).json()
    assert len(week) == 21
    assert week[0]["note"] == "в гостях" and week[0]["recipe_id"] is None   # planned meals stay
    assert [w["slug"] for w in week[:3]] == [None, "omelette", "chicken-legs-air-fryer"]
    assert week[4]["note"] == "Окорочка со вчера"


async def test_items_in_another_unit_are_not_taken_for_the_product(app, client):
    """'Лимон, 1 шт' is not 1 g of lemons: the catalog skips such packs, an order line
    still gets the product but adds nothing to the pantry."""
    from api.dependencies import catalog_service_factory
    from app.clients.wolt_catalog import CatalogItem
    from app.repositories.products import ProductRepository

    class Catalog:
        async def search(self, venue_slug, query):
            return [CatalogItem("by-weight", "Лимон ~500 г", 300, 500.0, None, "g"),
                    CatalogItem("by-piece", "Лимон, 1 шт", 90, 1.0, None, "pcs")]

    async with app.state.db.transaction() as session:
        lemon = await ProductRepository(session).get_one("lemon")
        assert await catalog_service_factory(Catalog())(session).refresh_product(lemon) == 1

    order = {"id": "lemons", "venue_name": "Wolt Market Batumi", "ordered_at": NOW_MS,
             "items": [{"id": None, "name": "Лимон, 1 шт", "count": 2}]}
    assert (await client.post("/wolt-orders", json={"orders": [order]})).json()["pantry_items"] == 0
    [saved] = (await client.get("/wolt-orders")).json()
    assert saved["items"][0]["product_key"] == "lemon"
