"""The web app against a real Postgres: migrations, seed data, the API and the unit of work.
Needs TEST_DATABASE_URL (see conftest.py); skipped otherwise."""

import datetime as dt
import time

import pytest

from conftest import api_client, sign_up

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
        "orders": 1, "pantry_items": 2, "skipped_restaurants": 0, "skipped_unknown": 0, "skipped_old": 0,
        "menus_ordered": 0}
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
    nothing_skipped = {"skipped_restaurants": 0, "skipped_unknown": 0, "skipped_old": 0, "menus_ordered": 0}
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


async def test_pinned_products_show_what_to_buy(app, client):
    """«Всегда дома»: a pinned product is missing when it ran out, or fell below the least to keep."""
    await client.put("/pantry/milk", json={"amount": 700})
    await client.put("/pantry/eggs", json={"amount": 4})
    milk = (await client.put("/pantry/milk/pin", json={})).json()
    assert (milk["pinned"], milk["missing"], milk["min_amount"]) == (True, False, None)
    eggs = (await client.put("/pantry/eggs/pin", json={"min_amount": 10})).json()
    assert (eggs["missing"], eggs["min_text"]) == (True, "10 шт")
    assert (await client.put("/pantry/bread/pin", json={})).json()["missing"]   # none at home

    items = {p["key"]: p for p in (await client.get("/pantry")).json()}
    assert {k for k, p in items.items() if p["pinned"]} == {"milk", "eggs", "bread"}
    assert {k for k, p in items.items() if p["missing"]} == {"eggs", "bread"}

    assert not (await client.put("/pantry/eggs", json={"amount": 10})).json()["missing"]   # bought enough
    assert (await client.put("/pantry/milk", json={"amount": 0})).json()["missing"]   # ran out
    assert (await client.put("/pantry/eggs/pin", json={"min_amount": None})).json()["min_amount"] is None
    bread = (await client.delete("/pantry/bread/pin")).json()
    assert (bread["pinned"], bread["missing"]) == (False, False)

    assert (await client.put("/pantry/eggs/pin", json={"min_amount": 0})).status_code == 422
    assert (await client.put("/pantry/nope/pin", json={})).status_code == 404

    async with api_client(app) as other:   # pins are per user
        await sign_up(other, "boris")
        assert not any(p["pinned"] for p in (await other.get("/pantry")).json())


async def test_own_timer_sound(app, client):
    """The account's own timer sound: the file is the request body, one per user, served back as it came."""
    assert (await client.get("/timer-sound")).json() is None
    assert (await client.get("/timer-sound/file")).status_code == 404

    clip = b"ID3" + bytes(range(256)) * 40
    resp = await client.put("/timer-sound", params={"name": "C:\\sounds\\yamete.mp3"}, content=clip,
                            headers={"Content-Type": "audio/mpeg"})
    assert resp.status_code == 200, resp.text
    assert {k: resp.json()[k] for k in ("name", "content_type", "size")} == \
        {"name": "yamete.mp3", "content_type": "audio/mpeg", "size": len(clip)}
    assert (await client.get("/timer-sound")).json()["name"] == "yamete.mp3"
    file = await client.get("/timer-sound/file")
    assert (file.content, file.headers["content-type"]) == (clip, "audio/mpeg")
    assert (await client.get("/timer-sound/file", headers={"If-None-Match": file.headers["etag"]})).status_code == 304

    # a phone may send no type: the name tells
    wav = await client.put("/timer-sound", params={"name": "ding.wav"}, content=b"RIFF0000WAVE")
    assert wav.json()["content_type"].startswith("audio/")
    assert (await client.get("/timer-sound/file")).content == b"RIFF0000WAVE"

    for name, body, ctype in [("notes.txt", b"hello", "text/plain"), ("empty.mp3", b"", "audio/mpeg"),
                              ("film.mp3", b"0" * (2 * 1024 * 1024 + 1), "audio/mpeg")]:
        resp = await client.put("/timer-sound", params={"name": name}, content=body, headers={"Content-Type": ctype})
        assert resp.status_code == 400, name
    assert (await client.get("/timer-sound")).json()["name"] == "ding.wav"   # the one before stays

    async with api_client(app) as other:   # a sound per user
        await sign_up(other, "boris")
        assert (await other.get("/timer-sound")).json() is None
        assert (await other.get("/timer-sound/file")).status_code == 404

    assert (await client.delete("/timer-sound")).status_code == 204
    assert (await client.get("/timer-sound")).json() is None


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
    assert result == {"orders": 1, "pantry_items": 1, "skipped_restaurants": 1, "skipped_unknown": 1, "skipped_old": 1,
                      "menus_ordered": 0}
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


# ---------- week menu: draft -> awaiting order -> ordered ----------

def day(offset: int) -> str:
    return (dt.date.today() + dt.timedelta(days=offset)).isoformat()


def order_of(store, at_ms, order_id):
    """A Wolt order with exactly what the menu's list says to buy in this store."""
    return {"id": order_id, "venue_name": store["name"], "venue_url": store["url"], "ordered_at": at_ms,
            "items": [{"id": l["item"]["id"], "name": l["item"]["name"], "count": l["packs"]} for l in store["lines"]]}


async def test_menu_from_the_recipes_with_swaps(client):
    menu = (await client.post("/menus", json={"start": TODAY})).json()
    assert menu["status"] == "draft" and menu["last_day"] == day(6)
    meals = {(m["day"], m["meal"]): m for m in menu["meals"]}
    assert len(meals) == 21
    recipes = {r["id"]: r for r in (await client.get("/recipes")).json()}
    for m in menu["meals"]:
        if m["recipe_id"]:
            assert m["meal"] in recipes[m["recipe_id"]]["meals"] and m["swappable"]
        else:
            assert m["meal"] == "lunch" and m["note"].endswith(" со вчера") and not m["swappable"]

    # didn't like a breakfast: another one, nothing else changes
    old = meals[(day(2), "breakfast")]
    swapped = (await client.post(f"/menus/{menu['id']}/{day(2)}/breakfast/swap")).json()
    new = next(m for m in swapped["meals"] if (m["day"], m["meal"]) == (day(2), "breakfast"))
    assert new["recipe_id"] != old["recipe_id"] and "breakfast" in recipes[new["recipe_id"]]["meals"]
    assert sum(a != b for a, b in zip(menu["meals"], swapped["meals"])) == 1

    # a dinner decides tomorrow's lunch
    swapped = (await client.post(f"/menus/{menu['id']}/{day(1)}/dinner/swap")).json()
    after = {(m["day"], m["meal"]): m for m in swapped["meals"]}
    dinner, lunch = after[(day(1), "dinner")], after[(day(2), "lunch")]
    if dinner["multiplier"] == 2:
        assert lunch["note"] == f"{dinner['title']} со вчера"
    else:
        assert lunch["recipe_id"] and "lunch" in recipes[lunch["recipe_id"]]["meals"]
    # leftovers follow the dinner, they aren't swapped on their own
    leftovers = next(m for m in swapped["meals"] if not m["recipe_id"])
    assert (await client.post(f"/menus/{menu['id']}/{leftovers['day']}/lunch/swap")).status_code == 409
    assert (await client.post(f"/menus/{menu['id']}/{day(9)}/lunch/swap")).status_code == 404

    # the plan is the menu, and «Перемешать всё» keeps the same menu
    plan = (await client.get("/plan", params={"start": TODAY, "days": 7})).json()
    assert [p["recipe_id"] for p in plan] == [m["recipe_id"] for m in swapped["meals"]]
    again = (await client.post("/menus", json={"start": TODAY})).json()
    assert again["id"] == menu["id"]
    assert [m["id"] for m in (await client.get("/menus", params={"since": TODAY})).json()] == [menu["id"]]


async def test_menu_from_home(client):
    # at home: 10 eggs and 300 g of bread — fried eggs for two, twice; nothing else in the book
    await client.put("/pantry/eggs", json={"amount": 10})
    await client.put("/pantry/bread", json={"amount": 300})
    fried_eggs = next(r["id"] for r in (await client.get("/recipes")).json() if r["slug"] == "fried-eggs")
    # fried eggs already planned after the menu take their share first
    await client.put(f"/plan/{day(7)}/breakfast", json={"recipe_id": fried_eggs, "multiplier": 1})
    menu = (await client.post("/menus", json={"start": TODAY, "from_home": True})).json()
    assert menu["from_home"]
    assert [(m["day"], m["meal"], m["recipe_id"], m["missing"]) for m in menu["meals"]] == [
        (TODAY, "breakfast", fried_eggs, [])]

    # without them, twice; «Перемешать всё» keeps it from home
    await client.put(f"/plan/{day(7)}/breakfast", json={"recipe_id": None})
    menu = (await client.post("/menus", json={"start": TODAY, "from_home": True})).json()
    assert [(m["day"], m["meal"], m["recipe_id"]) for m in menu["meals"]] == [
        (TODAY, "breakfast", fried_eggs), (day(1), "breakfast", fried_eggs)]
    # all of it is at home: nothing to order
    order = (await client.get(f"/menus/{menu['id']}/order", params={"today": TODAY})).json()
    assert order["shopping"]["stores"] == [] and order["shopping"]["not_found"] == []

    # an empty meal gets a recipe, and what it needs from the shop shows
    names = {p["name"] for p in (await client.get("/pantry")).json()}
    menu = (await client.post(f"/menus/{menu['id']}/{day(3)}/lunch/swap")).json()
    lunch = next(m for m in menu["meals"] if (m["day"], m["meal"]) == (day(3), "lunch"))
    assert lunch["recipe_id"] and lunch["swappable"] and lunch["missing"] and set(lunch["missing"]) <= names
    # the second fried eggs -> no other breakfast is at home: one to buy; the first ones stay at home
    menu = (await client.post(f"/menus/{menu['id']}/{day(1)}/breakfast/swap")).json()
    first, second = (next(m for m in menu["meals"] if (m["day"], m["meal"]) == (d, "breakfast")) for d in (TODAY, day(1)))
    assert (first["recipe_id"], first["missing"]) == (fried_eggs, [])
    assert second["recipe_id"] != fried_eggs and second["missing"]

    # a menu that isn't from home doesn't count what's at home
    menu = (await client.post("/menus", json={"start": TODAY})).json()
    assert not menu["from_home"] and len(menu["meals"]) == 21 and not any(m["missing"] for m in menu["meals"])


async def test_menu_keeps_cooked_meals(client):
    plan = (await client.get("/plan", params={"start": TODAY, "days": 1})).json()
    await client.post(f"/plan/{TODAY}/breakfast/cooked", json={"cooked": True})
    menu = (await client.post("/menus", json={"start": TODAY})).json()
    breakfast = menu["meals"][0]
    assert breakfast["recipe_id"] == plan[0]["recipe_id"] and breakfast["cooked_at"] and not breakfast["swappable"]
    assert (await client.post(f"/menus/{menu['id']}/{TODAY}/breakfast/swap")).status_code == 409


async def test_menu_status_flow_and_order_sync(client):
    menu = (await client.post("/menus", json={"start": TODAY})).json()
    url = f"/menus/{menu['id']}"
    # the menu is random among 82 recipes: make sure it has meat and groceries to order
    legs_recipe = next(r["id"] for r in (await client.get("/recipes")).json() if r["slug"] == "chicken-legs-air-fryer")
    await client.put(f"/plan/{day(1)}/dinner", json={"recipe_id": legs_recipe, "multiplier": 2})
    assert (await client.put(f"{url}/status", json={"status": "ordered"})).status_code == 409
    confirmed = (await client.put(f"{url}/status", json={"status": "awaiting_order"})).json()
    assert confirmed["status"] == "awaiting_order" and confirmed["confirmed_at"]
    assert (await client.post(f"{url}/{day(1)}/dinner/swap")).status_code == 409
    assert (await client.post("/menus", json={"start": day(3)})).status_code == 409   # overlaps the week
    assert [m["id"] for m in (await client.get("/menus", params={"status": "awaiting_order"})).json()] == [menu["id"]]

    order = (await client.get(f"{url}/order", params={"today": TODAY})).json()
    stores = {s["venue_slug"]: s for s in order["shopping"]["stores"]}
    assert set(stores) == {"wolt-market-batumi", "red-market-meat-store"}
    assert stores["red-market-meat-store"]["name"] == "Red Market (мясо)"
    legs = next(l for l in stores["red-market-meat-store"]["lines"] if l["product_key"] == "chicken_legs")
    assert legs["item"]["url"] in order["task"] and f"{legs['packs']} × {legs['item']['name']}" in order["task"]

    # an order placed before the menu went to ordering isn't the menu's (its food is at home all the same)
    now_ms = int(time.time() * 1000)
    before = {"id": "before", "venue_name": "Wolt Market Batumi", "ordered_at": now_ms - DAY_MS,
              "items": [{"id": None, "name": "Банан, 1 кг", "count": 1}]}
    meat = order_of(stores["red-market-meat-store"], now_ms, "meat")
    result = (await client.post("/wolt-orders", json={"orders": [before, meat]})).json()
    assert result["orders"] == 2 and result["menus_ordered"] == 0     # the groceries are still to buy
    menu = (await client.get(url)).json()
    assert menu["status"] == "awaiting_order" and [o["id"] for o in menu["orders"]] == ["meat"]
    left = (await client.get(f"{url}/order", params={"today": TODAY})).json()["shopping"]["stores"]
    assert [s["venue_slug"] for s in left] == ["wolt-market-batumi"]

    groceries = order_of(left[0], now_ms, "groceries")
    assert (await client.post("/wolt-orders", json={"orders": [groceries]})).json()["menus_ordered"] == 1
    menu = (await client.get(url)).json()
    assert menu["status"] == "ordered" and menu["ordered_at"]
    assert {o["id"] for o in menu["orders"]} == {"meat", "groceries"}
    assert (await client.get(f"{url}/order", params={"today": TODAY})).json()["shopping"]["stores"] == []

    # undo and back to draft: one step at a time
    assert (await client.put(f"{url}/status", json={"status": "draft"})).status_code == 409
    assert (await client.put(f"{url}/status", json={"status": "awaiting_order"})).json()["ordered_at"] is None
    draft = (await client.put(f"{url}/status", json={"status": "draft"})).json()
    assert draft["status"] == "draft" and draft["confirmed_at"] is None


async def test_menus_in_a_row(client):
    this = (await client.post("/menus", json={"start": TODAY})).json()
    await client.put(f"/menus/{this['id']}/status", json={"status": "awaiting_order"})
    following = (await client.post("/menus", json={"start": day(7)})).json()
    assert [m["id"] for m in (await client.get("/menus", params={"since": TODAY})).json()] == [this["id"], following["id"]]
    # a draft is simply put together anew when a new menu takes its days
    later = (await client.post("/menus", json={"start": day(10)})).json()
    menus = (await client.get("/menus", params={"since": TODAY})).json()
    assert [(m["id"], m["start"]) for m in menus] == [(this["id"], TODAY), (later["id"], day(10))]
    assert (await client.get(f"/menus/{following['id']}")).status_code == 404
    assert [m["id"] for m in (await client.get("/menus", params={"since": day(7)})).json()] == [later["id"]]
