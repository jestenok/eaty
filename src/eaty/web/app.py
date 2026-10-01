"""Web app: daily recipes with step timers, shopping list priced from Wolt, pantry from Wolt orders."""

from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from importlib import resources

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.engine import URL, Connection

from eaty.config import load_dotenv
from eaty.web import seed
from eaty.web.db import ConfigError, database_url, make_engine, make_sessionmaker, needs_selector_loop
from eaty.web.routers import pantry, plan, recipes, shopping
from eaty.web.services.catalog import CatalogJob

STATIC = resources.files("eaty.web").joinpath("static")
MIGRATIONS = resources.files("eaty.web").joinpath("migrations")


def upgrade_schema(connection: Connection) -> None:
    """`alembic upgrade head` on an existing connection (called through run_sync)."""
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS))
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


def create_app(url: URL | str | None = None, city: str = "batumi", migrate: bool = True,
               engine_options: dict | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(url, **(engine_options or {}))
        app.state.sessions = make_sessionmaker(engine)
        app.state.catalog_job = CatalogJob(app.state.sessions)
        app.state.city = city
        if migrate:
            async with engine.begin() as conn:
                await conn.run_sync(upgrade_schema)
        async with app.state.sessions() as session:
            await seed.seed(session)
        yield
        await engine.dispose()

    app = FastAPI(title="eaty", version="0.2.0", lifespan=lifespan)
    for module in (plan, recipes, shopping, pantry):
        app.include_router(module.router)

    @app.get("/api/health", tags=["health"])
    async def health(request: Request):
        async with request.app.state.sessions() as session:
            await session.execute(text("select 1"))
        return {"ok": True}

    @app.middleware("http")
    async def revalidate_static(request: Request, call_next):
        """The phone must not keep an old app.js after an update: always revalidate (ETag)."""
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(STATIC.joinpath("index.html")))

    return app


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    load_dotenv()
    p = argparse.ArgumentParser(prog="eaty-web", description="Рецепты на каждый день, таймеры и продукты из Wolt.")
    p.add_argument("--host", default=os.environ.get("EATY_HOST", "127.0.0.1"),
                   help="адрес; для телефона оставь 127.0.0.1 и открой через `tailscale serve`")
    p.add_argument("--port", type=int, default=int(os.environ.get("EATY_PORT", "8000")))
    p.add_argument("--no-migrate", action="store_true", help="не накатывать миграции при старте")
    args = p.parse_args(argv)
    try:
        url = database_url()
    except ConfigError as exc:
        raise SystemExit(str(exc))
    app = create_app(url, city=os.environ.get("EATY_WOLT_CITY", "batumi"), migrate=not args.no_migrate)
    server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port))
    # uvicorn would pick the Proactor loop on Windows; psycopg needs a selector loop.
    loop_factory = asyncio.SelectorEventLoop if needs_selector_loop(url) else None
    asyncio.run(server.serve(), loop_factory=loop_factory)
    return 0
