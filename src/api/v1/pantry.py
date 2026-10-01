from fastapi import APIRouter

from api.dependencies import PantryServiceDep
from app.schemas.pantry import PantryItemOut, PantryLevelIn, PantryPinIn

router = APIRouter()


@router.get("", summary="Что есть дома", response_model=list[PantryItemOut])
async def get_pantry(service: PantryServiceDep):
    return await service.items()


@router.put("/{product_key}", summary="Поправить, сколько продукта дома", response_model=PantryItemOut)
async def set_level(service: PantryServiceDep, product_key: str, dto: PantryLevelIn):
    return await service.set_level(product_key, dto.amount)


@router.put("/{product_key}/pin", summary="«Всегда дома»: закрепить продукт (и сколько держать дома минимум)",
            response_model=PantryItemOut)
async def pin(service: PantryServiceDep, product_key: str, dto: PantryPinIn):
    return await service.pin(product_key, dto.min_amount)


@router.delete("/{product_key}/pin", summary="Открепить продукт из «Всегда дома»", response_model=PantryItemOut)
async def unpin(service: PantryServiceDep, product_key: str):
    return await service.unpin(product_key)
