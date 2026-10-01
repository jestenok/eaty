from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Engine and session factory, created once per app and passed around explicitly.

    `transaction()` is the unit of work and the only place that commits: services and
    repositories just change the session, whoever opened the transaction (a request or
    a background job) decides when it ends.
    """

    def __init__(self, url: URL | str, *, echo: bool = False, **engine_options):
        pooling = {} if "poolclass" in engine_options else {"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800}
        self.engine = create_async_engine(url, echo=echo, pool_pre_ping=True, **pooling, **engine_options)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Commit when the block finishes, roll back when it raises."""
        async with self.session_factory() as session, session.begin():
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
