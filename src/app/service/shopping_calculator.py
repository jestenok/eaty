"""Shopping list: what the meal plan needs minus what is at home, priced from Wolt."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

WOLT_VENUE_URL = "https://wolt.com/ru/geo/{city}/venue/{venue}"
WOLT_ITEM_URL = WOLT_VENUE_URL + "/itemid-{item}"


@dataclass(frozen=True)
class Offer:
    item_id: str
    venue_slug: str
    name: str
    price: int            # tetri per pack (or per weight step)
    pack_amount: float    # in the product's base unit
    preferred: bool = False
    by_weight: bool = False

    @property
    def unit_price(self) -> float:
        return self.price / self.pack_amount


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    base_unit: str
    venue_slug: str


@dataclass
class Line:
    product: Product
    need: float
    have: float
    offer: Offer | None
    packs: int = 0

    @property
    def to_buy(self) -> float:
        return max(self.need - self.have, 0.0)

    @property
    def cost(self) -> int:
        return self.packs * self.offer.price if self.offer else 0


@dataclass
class StoreBasket:
    venue_slug: str
    lines: list[Line] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(line.cost for line in self.lines)


def choose_offer(offers: list[Offer]) -> Offer | None:
    """The preferred item if it's on sale, otherwise the cheapest per gram / ml / piece."""
    usable = [o for o in offers if o.pack_amount and o.pack_amount > 0 and o.price > 0]
    if not usable:
        return None
    preferred = [o for o in usable if o.preferred]
    if preferred:
        return preferred[0]
    return min(usable, key=lambda o: o.unit_price)


def build(
    needs: dict[str, float],
    pantry: dict[str, float],
    products: dict[str, Product],
    offers: dict[str, list[Offer]],
) -> list[Line]:
    lines = []
    for key, need in needs.items():
        if need <= 0 or key not in products:
            continue
        offer = choose_offer(offers.get(key, []))
        line = Line(product=products[key], need=need, have=max(pantry.get(key, 0.0), 0.0), offer=offer)
        if offer and line.to_buy > 0:
            # Tiny remainders (a few grams of garlic) are not worth a whole extra pack.
            line.packs = math.ceil(line.to_buy / offer.pack_amount - 0.05)
        lines.append(line)
    return sorted(lines, key=lambda line: line.product.name)


def by_store(lines: list[Line]) -> list[StoreBasket]:
    stores: dict[str, StoreBasket] = {}
    for line in lines:
        if line.packs <= 0 or not line.offer:
            continue
        slug = line.offer.venue_slug
        stores.setdefault(slug, StoreBasket(slug)).lines.append(line)
    return sorted(stores.values(), key=lambda s: -s.total)


def item_url(offer: Offer, city: str = "batumi") -> str:
    return WOLT_ITEM_URL.format(city=city, venue=offer.venue_slug, item=offer.item_id)


def venue_url(venue_slug: str, city: str = "batumi") -> str:
    return WOLT_VENUE_URL.format(city=city, venue=venue_slug)
