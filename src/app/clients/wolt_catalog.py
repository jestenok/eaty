"""Public Wolt catalog search (the same one wolt.com uses, no login)."""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.utils.units import parse_amount

SEARCH_URL = "https://consumer-api.wolt.com/consumer-api/consumer-assortment/v1/venues/slug/{slug}/assortment/items/search"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eaty/0.3"


@dataclass(frozen=True)
class CatalogItem:
    id: str
    name: str
    price: int              # tetri per pack (or per weight step)
    pack_amount: float | None
    weight_step_g: int | None


def parse_item(raw: dict[str, Any]) -> CatalogItem | None:
    """One item of a search response. Prices come in tetri; sold-by-weight items
    have a per-kg price and a weight step."""
    if raw.get("disabled_info") or not raw.get("price"):
        return None
    weight = raw.get("sell_by_weight_config") or {}
    step = weight.get("grams_per_step")
    if step:
        per_kg = weight.get("price_per_kg") or raw["price"]
        return CatalogItem(raw["id"], raw["name"], round(per_kg * step / 1000), float(step), int(step))
    amount = parse_amount(raw.get("unit_info")) or parse_amount(raw.get("name"))
    return CatalogItem(raw["id"], raw["name"], int(raw["price"]), amount[0] if amount else None, None)


class WoltCatalogClient:
    """Created once per app (lifespan) and injected: one connection pool for all searches."""

    def __init__(self, language: str = "ru", http: httpx.AsyncClient | None = None):
        self.language = language
        self.http = http or httpx.AsyncClient(
            timeout=20, headers={"User-Agent": USER_AGENT, "Accept-Language": language})

    async def search(self, venue_slug: str, query: str) -> list[CatalogItem]:
        for attempt in range(4):  # Wolt answers 429 when asked too often
            resp = await self.http.post(
                SEARCH_URL.format(slug=venue_slug), params={"language": self.language}, json={"q": query})
            if resp.status_code != 429:
                break
            await asyncio.sleep(2 * (attempt + 1))
        resp.raise_for_status()
        items = (parse_item(raw) for raw in resp.json().get("items") or ())
        return [i for i in items if i]

    async def aclose(self) -> None:
        await self.http.aclose()
