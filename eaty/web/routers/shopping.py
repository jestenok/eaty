import datetime as dt
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eaty import shopping
from eaty.units import format_amount
from eaty.web.db import get_session
from eaty.web.models import MealPlan, Product, RecipeIngredient, WoltItem
from eaty.web.schemas import CatalogStatus, ShoppingItem, ShoppingLine, ShoppingList, ShoppingStore
from eaty.web.services import pantry

router = APIRouter(prefix="/api", tags=["shopping"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def needs_for(session: AsyncSession, start: dt.date, days: int) -> dict[str, float]:
    """Ingredients of the meals not cooked yet, times how many times each is cooked."""
    rows = await session.execute(
        select(RecipeIngredient.product_key, func.sum(RecipeIngredient.amount * MealPlan.multiplier))
        .join(MealPlan, MealPlan.recipe_id == RecipeIngredient.recipe_id)
        .where(MealPlan.day >= start, MealPlan.day < start + dt.timedelta(days=days),
               MealPlan.cooked_at.is_(None), RecipeIngredient.product_key.is_not(None))
        .group_by(RecipeIngredient.product_key))
    return {key: float(need) for key, need in rows}


async def offers_by_product(session: AsyncSession) -> dict[str, list[shopping.Offer]]:
    offers: dict[str, list[shopping.Offer]] = defaultdict(list)
    items = await session.scalars(select(WoltItem).where(
        WoltItem.available.is_(True), WoltItem.product_key.is_not(None), WoltItem.pack_amount > 0))
    for i in items:
        offers[i.product_key].append(shopping.Offer(
            i.id, i.venue_slug, i.name, i.price, i.pack_amount, preferred=i.preferred, by_weight=i.weight_step_g is not None))
    return offers


def line_out(line: shopping.Line, city: str) -> ShoppingLine:
    unit = line.product.base_unit
    offer = line.offer
    return ShoppingLine(
        product_key=line.product.key,
        product=line.product.name,
        need=format_amount(line.need, unit),
        have=format_amount(line.have, unit) if line.have else "",
        to_buy=format_amount(line.to_buy, unit) if line.to_buy else "",
        packs=line.packs,
        cost=line.cost,
        item=offer and ShoppingItem(name=offer.name, price=offer.price, pack=format_amount(offer.pack_amount, unit),
                                    by_weight=offer.by_weight, url=shopping.item_url(offer, city)),
    )


@router.get("/shopping", response_model=ShoppingList)
async def get_shopping(request: Request, session: Session, start: dt.date | None = None,
                       days: Annotated[int, Query(ge=1, le=31)] = 7):
    start = start or dt.date.today()
    city = request.app.state.city
    products = {p.key: shopping.Product(p.key, p.name, p.base_unit, p.venue_slug)
                for p in await session.scalars(select(Product))}
    lines = shopping.build(await needs_for(session, start, days), await pantry.levels(session),
                           products, await offers_by_product(session))
    stores = shopping.by_store(lines)
    updated = await session.scalar(select(func.max(WoltItem.fetched_at)).where(WoltItem.preferred.is_(False)))
    return ShoppingList(
        start=start, days=days, prices_updated_at=updated,
        stores=[ShoppingStore(venue_slug=s.venue_slug, total=s.total, lines=[line_out(l, city) for l in s.lines])
                for s in stores],
        enough=[line_out(l, city) for l in lines if l.offer and l.packs == 0],
        not_found=[line_out(l, city) for l in lines if not l.offer],
        total=sum(s.total for s in stores),
    )


@router.post("/catalog/refresh", status_code=202, response_model=CatalogStatus)
async def refresh_catalog(request: Request):
    job = request.app.state.catalog_job
    job.start()
    return CatalogStatus(running=job.running, last=job.last)


@router.get("/catalog/status", response_model=CatalogStatus)
async def catalog_status(request: Request):
    job = request.app.state.catalog_job
    return CatalogStatus(running=job.running, last=job.last)
