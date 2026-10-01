import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import ShoppingServiceDep
from app.schemas.shopping import ShoppingListOut

router = APIRouter()


@router.get("", summary="Список покупок по плану с ценами из Wolt", response_model=ShoppingListOut)
async def get_shopping(service: ShoppingServiceDep, start: dt.date | None = None,
                       days: Annotated[int, Query(ge=1, le=31)] = 7):
    return await service.build(start or dt.date.today(), days)
