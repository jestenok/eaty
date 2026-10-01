from typing import Annotated

from fastapi import APIRouter, Path

from api.dependencies import ProductServiceDep
from app.schemas.product import ProductIn, ProductOut

router = APIRouter()


@router.get("", summary="Продукты, которые покупаем в Wolt", response_model=list[ProductOut])
async def list_products(service: ProductServiceDep):
    return await service.list()


@router.put("/{key}", summary="Добавить продукт или поправить его поиск в Wolt", response_model=ProductOut)
async def put_product(service: ProductServiceDep, key: Annotated[str, Path(pattern=r"^[a-z0-9_]{1,64}$")],
                      dto: ProductIn):
    return await service.put(key, dto)
