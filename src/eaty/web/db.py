"""Database connection: async SQLAlchemy engine on asyncpg."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class ConfigError(RuntimeError):
    pass


ASYNC_DRIVERS = {"postgresql+asyncpg", "postgresql+psycopg", "postgresql+psycopg_async"}


def to_async_url(raw: str | URL, default_db: str | None = None) -> URL:
    """Any postgres URL -> an async one (asyncpg unless an async driver is given explicitly);
    adds the database name if the URL has none."""
    url = make_url(raw)
    if not url.drivername.startswith("postgres"):
        raise ConfigError(f"Нужен PostgreSQL, а в настройках {url.drivername}")
    if url.drivername not in ASYNC_DRIVERS:
        url = url.set(drivername="postgresql+asyncpg")
    if not url.database and default_db:
        url = url.set(database=default_db)
    return url


def needs_selector_loop(url: URL) -> bool:
    """psycopg's async mode can't run on Windows' default Proactor event loop (asyncpg can)."""
    return sys.platform == "win32" and url.drivername.startswith("postgresql+psycopg")


def use_selector_loop_on_windows(url: URL) -> None:
    """For code that creates its own loops via the policy (asyncio.run, anyio, TestClient)."""
    if needs_selector_loop(url):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def database_url() -> URL:
    """EATY_DATABASE_URL, or POSTGRES_URI (server) + EATY_DB_NAME (database, default eaty)."""
    raw = os.environ.get("EATY_DATABASE_URL") or os.environ.get("POSTGRES_URI")
    if not raw:
        raise ConfigError("Не задана база: впиши POSTGRES_URI или EATY_DATABASE_URL в .env")
    return to_async_url(raw, os.environ.get("EATY_DB_NAME", "eaty"))


def make_engine(url: URL | str | None = None, **options) -> AsyncEngine:
    """Pooled engine; `options` go to create_async_engine (a custom poolclass replaces the sizing)."""
    pooling = {} if "poolclass" in options else {"pool_size": 5, "max_overflow": 5}
    return create_async_engine(url or database_url(), pool_pre_ping=True, **pooling, **options)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with request.app.state.sessions() as session:
        yield session
