from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Base
from core.error import NotFoundError


class BaseRepository[TModel: Base]:
    """Data access for one model.

    Never commits or rolls back: the transaction belongs to whoever opened it (the
    request's unit of work or a background job). Writes are flushed so later queries
    in the same transaction see them and constraint errors surface right here.
    """

    model: type[TModel]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, *pk: Any) -> TModel | None:
        return await self.session.get(self.model, pk[0] if len(pk) == 1 else pk)

    async def get_one(self, *pk: Any) -> TModel:
        obj = await self.get(*pk)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} {', '.join(map(str, pk))} не найден")
        return obj

    async def find(self, *where: ColumnElement[bool], order_by: Sequence[Any] = (), limit: int | None = None) -> list[TModel]:
        query = select(self.model).where(*where).order_by(*order_by).limit(limit)
        return list((await self.session.scalars(query)).unique().all())

    async def exists(self, *where: ColumnElement[bool]) -> bool:
        return await self.session.scalar(select(select(self.model).where(*where).exists())) or False

    async def add(self, obj: TModel) -> TModel:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def add_all(self, objs: Iterable[TModel]) -> None:
        self.session.add_all(objs)
        await self.session.flush()

    async def delete_where(self, *where: ColumnElement[bool]) -> None:
        await self.session.execute(delete(self.model).where(*where))

    async def upsert(self, values: dict[str, Any] | list[dict[str, Any]], *, conflict: Sequence[str],
                     update: Iterable[str] | None = None) -> None:
        """INSERT … ON CONFLICT: `update` — columns to overwrite (all but the conflict ones
        by default; an empty list means DO NOTHING)."""
        stmt = insert(self.model).values(values)
        rows = values if isinstance(values, list) else [values]
        columns = [c for c in (update if update is not None else rows[0]) if c not in conflict]
        if columns:
            stmt = stmt.on_conflict_do_update(index_elements=list(conflict), set_={c: stmt.excluded[c] for c in columns})
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=list(conflict))
        await self.session.execute(stmt)
