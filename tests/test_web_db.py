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
    assert result == {"orders": 1, "pantry_items": 1, "skipped_restaurants": 1, "skipped_unknown": 1, "skipped_old": 1,
                      "menus_ordered": 0}
    assert [o["id"] for o in (await client.get("/wolt-orders")).json()] == ["store"]
    assert (await pantry(client))["banana"] == 1000


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
