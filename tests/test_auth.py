"""Accounts: signing up and in, and every user seeing only their own plan, pantry, orders and syncs.
Needs TEST_DATABASE_URL (see conftest.py); skipped otherwise."""

import datetime as dt

from conftest import TEST_DATABASE_URL, api_client, running_app, sign_up

TODAY = dt.date.today().isoformat()
ORDER = {"id": "o1", "venue_name": "Wolt Market Batumi", "items": [{"id": "66a0dd8b9dfb545d3cc3f96f", "name": "Яйца 15 шт.", "count": 1}]}
IMPORTED = {"orders": 1, "pantry_items": 1, "skipped_restaurants": 0, "skipped_unknown": 0, "skipped_old": 0,
            "menus_ordered": 0}


async def pantry(client) -> dict[str, float]:
    return {p["key"]: p["have"] for p in (await client.get("/pantry")).json()}


async def test_sign_up_in_and_out(anonymous):
    assert (await anonymous.get("/auth/me")).status_code == 401
    assert (await anonymous.get("/pantry")).status_code == 401
    assert (await anonymous.post("/catalog/refresh")).status_code == 401
    assert (await anonymous.get("/health")).status_code == 200

    assert (await sign_up(anonymous, " Anna ", "correct horse"))["login"] == "anna"
    assert (await anonymous.get("/auth/me")).json()["login"] == "anna"
    plan = (await anonymous.get("/plan", params={"start": TODAY, "days": 1})).json()
    assert [p["meal"] for p in plan] == ["breakfast", "lunch", "dinner"]  # a new user gets the default week

    assert (await anonymous.post("/auth/register", json={"login": "ANNA", "password": "another one"})).status_code == 409
    assert (await anonymous.post("/auth/register", json={"login": "bo", "password": "long enough"})).status_code == 422
    assert (await anonymous.post("/auth/register", json={"login": "boris", "password": "short"})).status_code == 422
    assert (await anonymous.post("/auth/register", json={"login": "bo ris", "password": "long enough"})).status_code == 422

    assert (await anonymous.post("/auth/logout")).status_code == 204
    assert (await anonymous.get("/auth/me")).status_code == 401

    wrong = await anonymous.post("/auth/login", json={"login": "anna", "password": "wrong horse"})
    assert (wrong.status_code, wrong.json()["detail"]) == (401, "Неверный логин или пароль")
    assert (await anonymous.post("/auth/login", json={"login": "nobody", "password": "correct horse"})).status_code == 401
    assert (await anonymous.post("/auth/login", json={"login": "Anna", "password": "correct horse"})).status_code == 200
    assert (await anonymous.get("/auth/me")).json()["login"] == "anna"


async def test_each_user_has_their_own_plan_pantry_and_orders(app):
    async with api_client(app) as anna, api_client(app) as boris:
        await sign_up(anna, "anna")
        await sign_up(boris, "boris")
        boris_day = (await boris.get("/plan", params={"start": TODAY, "days": 1})).json()

        await anna.put("/pantry/milk", json={"amount": 700})
        assert (await anna.post("/wolt-orders", json={"orders": [ORDER]})).json() == IMPORTED
        await anna.post("/wolt-orders/sync-log", json={"orders_found": 1, "orders_imported": 1, "pantry_items": 1})
        omelette = next(r["id"] for r in (await anna.get("/recipes")).json() if r["slug"] == "omelette")
        await anna.put(f"/plan/{TODAY}/lunch", json={"recipe_id": omelette, "multiplier": 1})
        await anna.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": True})

        assert (await pantry(boris))["milk"] == 0 and (await pantry(boris))["eggs"] == 0
        assert (await boris.get("/wolt-orders")).json() == []
        assert (await boris.get("/wolt-orders/sync-log")).json() == []
        assert len((await anna.get("/wolt-orders/sync-log")).json()) == 1
        assert (await boris.get("/plan", params={"start": TODAY, "days": 1})).json() == boris_day
        assert (await boris.get(f"/plan/{TODAY}/lunch/used")).json() == []

        # the same Wolt order seen in both browsers lands in both pantries, once each
        assert (await boris.post("/wolt-orders", json={"orders": [ORDER]})).json() == IMPORTED
        assert (await pantry(boris))["eggs"] == 15
        assert (await pantry(anna))["eggs"] == 10      # 15 bought, 5 went into the omelette
        assert len((await anna.get("/wolt-orders")).json()) == 1

        await boris.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": True})
        await boris.post(f"/plan/{TODAY}/lunch/cooked", json={"cooked": False})
        [_, lunch, _] = (await anna.get("/plan", params={"start": TODAY, "days": 1})).json()
        assert lunch["recipe_id"] == omelette and lunch["cooked_at"] is not None
        assert (await pantry(anna))["eggs"] == 10

        # week menus too: both can have one from the same day, neither sees the other's
        anna_menu = (await anna.post("/menus", json={"start": TODAY})).json()
        assert (await boris.get("/menus", params={"since": TODAY})).json() == []
        assert (await boris.get(f"/menus/{anna_menu['id']}")).status_code == 404
        boris_menu = (await boris.post("/menus", json={"start": TODAY})).json()
        assert boris_menu["id"] != anna_menu["id"]
        assert [m["id"] for m in (await anna.get("/menus", params={"since": TODAY})).json()] == [anna_menu["id"]]


async def test_the_extension_signs_in_with_a_token(app, client):
    resp = await client.post("/auth/token", json={"login": "anna", "password": "correct horse"})
    token = resp.json()["token"]
    assert resp.json()["user"]["login"] == "anna" and "set-cookie" not in resp.headers

    async with api_client(app) as extension:
        bearer = {"Authorization": f"Bearer {token}"}
        assert (await extension.get("/auth/me", headers=bearer)).json()["login"] == "anna"
        assert (await extension.post("/wolt-orders", json={"orders": [ORDER]}, headers=bearer)).status_code == 200
        assert (await extension.get("/auth/me", headers={"Authorization": "Bearer nope"})).status_code == 401

        assert (await extension.post("/auth/logout", headers=bearer)).status_code == 204
        assert (await extension.get("/auth/me", headers=bearer)).status_code == 401
    assert (await pantry(client))["eggs"] == 15   # the browser's own sign-in still works


async def test_the_extension_takes_the_sign_in_from_the_open_app(app, client, anonymous):
    resp = await client.post("/auth/extension-token")
    token = resp.json()["token"]
    assert resp.json()["user"]["login"] == "anna" and "set-cookie" not in resp.headers
    assert (await anonymous.post("/auth/extension-token")).status_code == 401

    assert (await client.post("/auth/logout")).status_code == 204  # signing out on the site
    async with api_client(app) as extension:                        # keeps the extension signed in
        bearer = {"Authorization": f"Bearer {token}"}
        assert (await extension.get("/auth/me", headers=bearer)).json()["login"] == "anna"
        assert (await extension.post("/wolt-orders", json={"orders": [ORDER]}, headers=bearer)).status_code == 200


async def test_sign_ins_expire(database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("SESSION_DAYS", "0")
    async with running_app(database) as app, api_client(app) as client:
        await sign_up(client)
        assert (await client.get("/auth/me")).status_code == 401


async def test_data_from_before_accounts_goes_to_the_first_sign_up(database, monkeypatch):
    from sqlalchemy import text

    from server import MIGRATIONS

    def upgrade_to(connection, revision):
        from alembic import command
        from alembic.config import Config

        cfg = Config()
        cfg.set_main_option("script_location", str(MIGRATIONS))
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, revision)

    async with database.engine.begin() as conn:  # the schema and data from before accounts
        await conn.run_sync(upgrade_to, "e5d5bf9e6564")
        await conn.execute(text(
            "insert into product (key, name, base_unit, venue_slug, search_q, match_re) values ('milk', 'Молоко', 'ml', '', '', '')"))
        await conn.execute(text("insert into pantry_entry (product_key, amount, source) values ('milk', 700, 'correction')"))
        await conn.execute(text(f"insert into meal_plan (day, meal, note) values ('{TODAY}', 'lunch', 'Кафе')"))

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    async with running_app(database) as app, api_client(app) as owner, api_client(app) as guest:
        assert (await owner.post("/auth/login", json={"login": "", "password": ""})).status_code == 401

        await sign_up(owner, "owner")
        assert (await pantry(owner))["milk"] == 700
        plan = (await owner.get("/plan", params={"start": TODAY, "days": 1})).json()
        assert [(p["meal"], p["note"]) for p in plan] == [("lunch", "Кафе")]  # had a plan: no default week on top

        await sign_up(guest, "guest")
        assert (await pantry(guest))["milk"] == 0
