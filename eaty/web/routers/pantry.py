from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eaty.units import format_amount
from eaty.web.db import get_session
from eaty.web.models import Product, WoltOrder
from eaty.web.schemas import ImportResult, OrderOut, OrdersIn, PantryItem, PantrySet
from eaty.web.services import orders, pantry

router = APIRouter(prefix="/api", tags=["pantry"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/pantry", response_model=list[PantryItem])
async def get_pantry(session: Session):
    have = await pantry.levels(session)
    return [
        PantryItem(key=p.key, name=p.name, base_unit=p.base_unit, have=have.get(p.key, 0.0),
                   have_text=format_amount(max(have.get(p.key, 0.0), 0.0), p.base_unit))
        for p in await session.scalars(select(Product).order_by(Product.name))
    ]


@router.put("/pantry/{product_key}", response_model=PantryItem)
async def set_pantry(session: Session, product_key: str, body: PantrySet):
    product = await session.get(Product, product_key)
    if product is None:
        raise HTTPException(404, "Нет такого продукта")
    await pantry.set_level(session, product_key, body.amount)
    await session.commit()
    return PantryItem(key=product.key, name=product.name, base_unit=product.base_unit, have=body.amount,
                      have_text=format_amount(body.amount, product.base_unit))


@router.post("/wolt/orders", response_model=ImportResult)
async def post_orders(session: Session, body: OrdersIn):
    """Called by the Chrome extension with the orders it saw on wolt.com."""
    return await orders.import_orders(session, body.orders)


@router.get("/wolt/orders", response_model=list[OrderOut])
async def get_orders(session: Session, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    rows = await session.scalars(
        select(WoltOrder).order_by(WoltOrder.ordered_at.desc().nulls_last(), WoltOrder.imported_at.desc()).limit(limit))
    return rows.all()
