from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import OrderServiceDep
from app.schemas.wolt_order import ImportResultOut, WoltOrderOut, WoltOrdersIn

router = APIRouter()


@router.post("", summary="Заказы с wolt.com от расширения Chrome", response_model=ImportResultOut)
async def import_orders(service: OrderServiceDep, dto: WoltOrdersIn):
    return await service.import_orders(dto.orders)


@router.get("", summary="Последние импортированные заказы", response_model=list[WoltOrderOut])
async def latest(service: OrderServiceDep, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return await service.latest(limit)
