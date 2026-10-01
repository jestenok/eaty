"""Items of the public Wolt catalog search (the same one wolt.com uses, no login)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from eaty.units import parse_amount

SEARCH_URL = "https://consumer-api.wolt.com/consumer-api/consumer-assortment/v1/venues/slug/{slug}/assortment/items/search"


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


def matches(name: str, match_re: str, exclude_re: str) -> bool:
    return bool(re.search(match_re, name, re.IGNORECASE)) and not (
        exclude_re and re.search(exclude_re, name, re.IGNORECASE)
    )
