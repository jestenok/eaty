from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import OrderServiceDep
from app.schemas.wolt_order import ImportResultOut, SyncLogIn, SyncLogOut, WoltOrderOut, WoltOrdersIn

router = APIRouter()


@router.post("", summary="Заказы с wolt.com от расширения Chrome", response_model=ImportResultOut)
async def import_orders(service: OrderServiceDep, dto: WoltOrdersIn):
    return await service.import_orders(dto.orders)


@router.get("", summary="Последние импортированные заказы", response_model=list[WoltOrderOut])
async def latest(service: OrderServiceDep, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return await service.latest(limit)


@router.post("/sync-log", summary="Итог синхронизации с Wolt от расширения", response_model=SyncLogOut)
async def log_sync(service: OrderServiceDep, dto: SyncLogIn):
    return await service.log_sync(dto)


@router.get("/sync-log", summary="Последние синхронизации с Wolt", response_model=list[SyncLogOut])
async def sync_history(service: OrderServiceDep, limit: Annotated[int, Query(ge=1, le=50)] = 5):
    return await service.sync_history(limit)
