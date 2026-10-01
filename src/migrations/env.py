"""Alembic environment. Works two ways:

- from the command line: `alembic upgrade head` (database from .env, async engine);
- from the app on startup: a sync connection is passed in `config.attributes["connection"]`.
"""

import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from config import get_config
from core.db import Base, to_async_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url():
    url = config.get_main_option("sqlalchemy.url")
    return to_async_url(url) if url else get_config().DATABASE_URL


def needs_selector_loop(url) -> bool:
    """psycopg's async mode can't run on Windows' default Proactor event loop (asyncpg can)."""
    return sys.platform == "win32" and url.drivername.startswith("postgresql+psycopg")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(url) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        do_run_migrations(connection)
    else:
        url = get_url()
        loop_factory = asyncio.SelectorEventLoop if needs_selector_loop(url) else None
        asyncio.run(run_async_migrations(url), loop_factory=loop_factory)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
