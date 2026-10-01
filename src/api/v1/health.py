from fastapi import APIRouter
from sqlalchemy import text

from core.fastapi.dependencies import SessionDep

router = APIRouter()


@router.get("", summary="Живо ли приложение и база")
async def health(session: SessionDep):
    await session.execute(text("select 1"))
    return {"ok": True}
