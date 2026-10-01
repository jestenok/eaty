import datetime as dt
from collections import defaultdict

from app.repositories.meal_plans import MealPlanRepository
from app.repositories.products import ProductRepository
from app.repositories.wolt_items import WoltItemRepository
from app.schemas.shopping import ShoppingItemOut, ShoppingLineOut, ShoppingListOut, ShoppingStoreOut
from app.service import shopping_calculator as calc
from app.service.pantry import PantryService
from app.utils.units import format_amount

# How the stores of the recipe book's products are called; any other store shows its slug.
STORES = {"wolt-market-batumi": "Wolt Market Batumi", "red-market-meat-store": "Red Market (мясо)"}


class ShoppingService:
    """What the plan needs minus what's at home, priced with items from Wolt."""

    def __init__(self, plans: MealPlanRepository, products: ProductRepository, items: WoltItemRepository,
                 pantry: PantryService, city: str):
        self.plans = plans
        self.products = products
        self.items = items
        self.pantry = pantry
        self.city = city

    async def build(self, start: dt.date, days: int) -> ShoppingListOut:
        products = {p.key: calc.Product(p.key, p.name, p.base_unit, p.venue_slug) for p in await self.products.all()}
        offers: dict[str, list[calc.Offer]] = defaultdict(list)
        for i in await self.items.offers():
            offers[i.product_key].append(calc.Offer(
                i.id, i.venue_slug, i.name, i.price, i.pack_amount, preferred=i.preferred,
                by_weight=i.weight_step_g is not None))
        lines = calc.build(await self.plans.needs_between(start, days), await self.pantry.levels(), products, offers)
        stores = calc.by_store(lines)
        return ShoppingListOut(
            start=start, days=days, prices_updated_at=await self.items.last_refresh(),
            stores=[ShoppingStoreOut(venue_slug=s.venue_slug, name=STORES.get(s.venue_slug, s.venue_slug),
                                     url=calc.venue_url(s.venue_slug, self.city), total=s.total,
                                     lines=[self._line_out(l) for l in s.lines])
                    for s in stores],
            enough=[self._line_out(l) for l in lines if l.offer and l.packs == 0],
            not_found=[self._line_out(l) for l in lines if not l.offer],
            total=sum(s.total for s in stores),
        )

    def _line_out(self, line: calc.Line) -> ShoppingLineOut:
        unit = line.product.base_unit
        offer = line.offer
        return ShoppingLineOut(
            product_key=line.product.key,
            product=line.product.name,
            need=format_amount(line.need, unit),
            have=format_amount(line.have, unit) if line.have else "",
            to_buy=format_amount(line.to_buy, unit) if line.to_buy else "",
            packs=line.packs,
            cost=line.cost,
            item=offer and ShoppingItemOut(
                id=offer.item_id, name=offer.name, price=offer.price, pack=format_amount(offer.pack_amount, unit),
                by_weight=offer.by_weight, url=calc.item_url(offer, self.city)),
        )
