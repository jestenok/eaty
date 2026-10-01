from sqlalchemy.engine import URL, make_url

from core.error import ConfigError

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
