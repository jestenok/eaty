from fastapi import APIRouter

from api.dependencies import PantryServiceDep
from app.schemas.pantry import PantryItemOut, PantryLevelIn

router = APIRouter()


@router.get("", summary="Что есть дома", response_model=list[PantryItemOut])
async def get_pantry(service: PantryServiceDep):
    return await service.items()


@router.put("/{product_key}", summary="Поправить, сколько продукта дома", response_model=PantryItemOut)
async def set_level(service: PantryServiceDep, product_key: str, dto: PantryLevelIn):
    return await service.set_level(product_key, dto.amount)
