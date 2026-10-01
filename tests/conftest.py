import pytest

# Delivery point used across tests (central Tbilisi).
HOME = (41.7000, 44.8000)


def venue(id, name, lat, lon, score=9.2, online=True, delivers=True, tags=("burger",), **extra):
    raw = {
        "id": id,
        "slug": f"{id}-slug",
        "name": name,
        "location": [lon, lat],
        "online": online,
        "delivers": delivers,
        "estimate_range": "25-35",
        "delivery_price": "₾2.99",
        "price_range": 2,
        "tags": list(tags),
        "short_description": "",
        "address": "Some st. 1",
        "city": "Tbilisi",
        "country": "GEO",
        **extra,
    }
    if score is not None:
        raw["rating"] = {"rating": 4, "score": score}
    return raw


@pytest.fixture
def page():
    """Shape of GET consumer-api.wolt.com/v1/pages/restaurants."""
    near_best = venue("a", "Near Best", 41.7030, 44.8000, score=9.6)          # ~330 m
    return {
        "name": "restaurants",
        "sections": [
            {
                "name": "popular",
                "items": [{"title": "Near Best", "venue": near_best}],
            },
            {
                "name": "restaurants-delivering-venues",
                "items": [
                    {"title": "Near Best", "venue": near_best},  # duplicate across sections
                    {"venue": venue("b", "Near Good", 41.7050, 44.8000, score=9.1, tags=("sushi",))},  # ~560 m
                    {"venue": venue("c", "Near Meh", 41.7010, 44.8000, score=8.2)},   # ~110 m, low score
                    {"venue": venue("d", "Far Great", 41.7200, 44.8000, score=9.8)},  # ~2.2 km
                    {"venue": venue("e", "Near Closed", 41.7020, 44.8000, score=9.7, online=False)},
                    {"venue": venue("f", "Near Unrated", 41.7020, 44.8000, score=None)},
                    {"venue": venue("g", "No Location", 0, 0, location=None)},
                    {"title": "banner without venue"},
                ],
            },
        ],
    }


# ---------- web app against a real Postgres ----------
#
# Runs only with TEST_DATABASE_URL. The database is WIPED (schema public is recreated), so it
# must be a local server or a database with "test" in its name. Without installing Postgres:
# an in-memory PGlite server (see README), driver psycopg.

import asyncio  # noqa: E402
import contextlib  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if TEST_DATABASE_URL and sys.platform == "win32" and "+psycopg" in TEST_DATABASE_URL:
    # psycopg's async mode can't run on Windows' default Proactor event loop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _test_url():
    from core.db import to_async_url

    url = to_async_url(TEST_DATABASE_URL)
    assert url.host in ("127.0.0.1", "localhost") or "test" in (url.database or ""), \
        "тесты стирают базу: нужен локальный сервер или база с «test» в имени"
    return url


@pytest.fixture
async def database():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    from sqlalchemy import text
    from sqlalchemy.pool import NullPool

    from core.db import Database

    url = _test_url()
    # PGlite runs every connection in one backend, so psycopg's named prepared statements
    # from different connections collide there. A real server doesn't need this.
    connect_args = {"prepare_threshold": None} if url.drivername.startswith("postgresql+psycopg") else {}
    db = Database(url, poolclass=NullPool, connect_args=connect_args)
    async with db.engine.begin() as conn:
        await conn.execute(text("drop schema public cascade"))
        await conn.execute(text("create schema public"))
    yield db
    await db.dispose()


@contextlib.asynccontextmanager
async def running_app(database):
    """The real app (migrations + seed in lifespan) on the test database.

    The lifespan runs in a task of its own, as under uvicorn: it holds the MCP session manager's
    task group, which must be left from the task that entered it, and pytest-asyncio tears
    fixtures down in another task than it set them up in."""
    from config import AppConfig
    from server import create_app

    application = create_app(AppConfig(), database=database)
    started, stop = asyncio.Event(), asyncio.Event()

    async def lifespan():
        async with application.router.lifespan_context(application):
            started.set()
            await stop.wait()

    task, waiter = asyncio.create_task(lifespan()), asyncio.create_task(started.wait())
    await asyncio.wait([task, waiter], return_when=asyncio.FIRST_COMPLETED)
    waiter.cancel()
    if task.done():
        task.result()  # the startup failed: raise its error here
    try:
        yield application
    finally:
        stop.set()
        await task


def api_client(app):
    """Not signed in yet; keeps the session cookie once it signs in."""
    from httpx import ASGITransport, AsyncClient

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1")


async def sign_up(client, login="anna", password="correct horse"):
    resp = await client.post("/auth/register", json={"login": login, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
async def app(database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    async with running_app(database) as application:
        yield application


@pytest.fixture
async def anonymous(app):
    async with api_client(app) as c:
        yield c


@pytest.fixture
async def client(app):
    """Signed in as a new user."""
    async with api_client(app) as c:
        await sign_up(c)
        yield c
