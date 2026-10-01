from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Database


def get_database(request: Request) -> Database:
    return request.app.state.db


async def get_session(database: Annotated[Database, Depends(get_database)]) -> AsyncIterator[AsyncSession]:
    """The request's unit of work: one transaction for everything the handler does."""
    async with database.transaction() as session:
        yield session


# scope="function": the transaction commits when the handler returns, BEFORE the response
# is sent. With the default scope the commit would run after the client already got
# "200 OK", and a failed commit would go unnoticed.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
