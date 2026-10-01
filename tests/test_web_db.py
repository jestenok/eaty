"""The web app against a real Postgres: migrations, seed data and the API.

Runs only when EATY_TEST_DATABASE_URL is set. The database is WIPED (schema public is
recreated), so it must be a local server or a database whose name contains "test".
Quick local option without installing Postgres: an in-memory PGlite server, see README.
"""

import asyncio
import datetime as dt
import os

import pytest

RAW_URL = os.environ.get("EATY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not RAW_URL, reason="EATY_TEST_DATABASE_URL не задан")


def _url():
    from eaty.web.db import to_async_url

    url = to_async_url(RAW_URL)
    assert url.host in ("127.0.0.1", "localhost") or "test" in (url.database or ""), \
        "тесты стирают базу: нужен локальный сервер или база с «test» в имени"
    return url


def _engine_options(url):
    from sqlalchemy.pool import NullPool

    # PGlite runs every connection in one backend, so psycopg's named prepared statements
    # from different connections collide there. A real server doesn't need this.
    connect_args = {"prepare_threshold": None} if url.drivername.startswith("postgresql+psycopg") else {}
    return {"poolclass": NullPool, "connect_args": connect_args}


async def _wipe(url):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, **_engine_options(url))
    async with engine.begin() as conn:
        await conn.execute(text("drop schema public cascade"))
        await conn.execute(text("create schema public"))
    await engine.dispose()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eaty.web.app import create_app
    from eaty.web.db import use_selector_loop_on_windows

    url = _url()
    use_selector_loop_on_windows(url)
    asyncio.run(_wipe(url))
    with TestClient(create_app(url, engine_options=_engine_options(url))) as c:
        yield c


def test_migrations_and_seed_give_a_planned_day_with_timers(client):
    today = dt.date.today().isoformat()
    plan = client.get("/api/plan", params={"start": today, "days": 1}).json()
    assert [p["meal"] for p in plan] == ["breakfast", "lunch", "dinner"]
    recipe = client.get(f"/api/recipes/{plan[2]['recipe_id']}").json()
    assert recipe["title"] == "Окорочка с картошкой в аэрогриле"
    assert sum(s["timer_seconds"] or 0 for s in recipe["steps"]) == (15 + 17 + 5) * 60


def test_order_fills_pantry_and_cooking_uses_it(client):
    order = {"id": "o1", "venue_name": "Wolt Market Batumi", "ordered_at": 1790848000000, "items": [
        {"id": "66a0dd8b9dfb545d3cc3f96f", "name": "Яйца 15 шт.", "count": 1},
        {"id": None, "name": "Картофель (ц), ~1000 г", "count": 2},
        {"id": None, "name": "Шоколад Alpen Gold", "count": 1},
    ]}
    assert client.post("/api/wolt/orders", json={"orders": [order]}).json() == {"orders": 1, "pantry_items": 2}
    client.post("/api/wolt/orders", json={"orders": [order]})  # the same order again must not double up
    pantry = {p["key"]: p["have"] for p in client.get("/api/pantry").json()}
    assert pantry["eggs"] == 15 and pantry["potato"] == 2000

    [saved] = client.get("/api/wolt/orders").json()
    assert [i["product_key"] for i in saved["items"]] == ["eggs", "potato", None]

    today = dt.date.today().isoformat()
    omelette = next(r["id"] for r in client.get("/api/recipes").json() if r["slug"] == "omelette")
    client.put(f"/api/plan/{today}/lunch", json={"recipe_id": omelette, "multiplier": 1})
    client.post(f"/api/plan/{today}/lunch/cooked", json={"cooked": True})
    assert {p["key"]: p["have"] for p in client.get("/api/pantry").json()}["eggs"] == 10
    client.post(f"/api/plan/{today}/lunch/cooked", json={"cooked": False})
    assert {p["key"]: p["have"] for p in client.get("/api/pantry").json()}["eggs"] == 15


def test_pantry_correction(client):
    assert client.put("/api/pantry/milk", json={"amount": 700}).json()["have"] == 700
    assert {p["key"]: p["have"] for p in client.get("/api/pantry").json()}["milk"] == 700
    assert client.put("/api/pantry/nope", json={"amount": 1}).status_code == 404


def test_shopping_list_prices_in_two_stores(client):
    data = client.get("/api/shopping", params={"start": dt.date.today().isoformat(), "days": 7}).json()
    assert {s["venue_slug"] for s in data["stores"]} == {"wolt-market-batumi", "red-market-meat-store"}
    assert data["total"] == sum(s["total"] for s in data["stores"]) > 0
    legs = next(l for s in data["stores"] for l in s["lines"] if l["product_key"] == "chicken_legs")
    assert legs["item"]["by_weight"] and legs["item"]["url"].endswith("itemid-c71af1cad259d733a9205145")


def test_bad_input_is_rejected(client):
    assert client.put("/api/plan/2026-10-01/supper", json={}).status_code == 422
    assert client.put("/api/plan/2026-10-01/lunch", json={"recipe_id": 999}).status_code == 404
    assert client.post("/api/wolt/orders", json={"orders": [{"id": "x", "items": []}]}).status_code == 422
