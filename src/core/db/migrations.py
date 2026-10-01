"""Running Alembic from the app (on startup) instead of the command line."""

from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy.engine import Connection

from core.db.session import Database


def _upgrade(connection: Connection, script_location: str) -> None:
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", script_location)
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


async def upgrade_to_head(database: Database, script_location: str | Path) -> None:
    """`alembic upgrade head` on the app's own engine, in one transaction."""
    async with database.engine.begin() as connection:
        await connection.run_sync(_upgrade, str(script_location))
