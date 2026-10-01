"""Client for Wolt's consumer API (the same one wolt.com uses).

Wolt has no official public API for customers. Browsing venues works without
logging in: the listing endpoint only needs the delivery coordinates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import requests

API_BASE = "https://consumer-api.wolt.com"
WEB_BASE = "https://wolt.com"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) eaty/0.1"


class WoltError(RuntimeError):
    pass


@dataclass(frozen=True)
class Venue:
    id: str
    slug: str
    name: str
    lat: float
    lon: float
    score: float | None  # 0-10, as shown in the app; None for venues without enough reviews
    online: bool
    delivers: bool
    estimate_range: str | None = None
    delivery_price: str | None = None
    price_range: int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    address: str = ""
    city: str = ""
    country: str = ""

    @property
    def is_open(self) -> bool:
        return self.online and self.delivers

    def url(self, language: str = "ru") -> str:
        if not (self.country and self.city):
            return f"{WEB_BASE}/{language}/search?q={self.slug}"
        city = re.sub(r"[^a-z0-9]+", "-", self.city.lower()).strip("-")
        return f"{WEB_BASE}/{language}/{self.country.lower()}/{city}/restaurant/{self.slug}"


def _parse_venue(raw: dict[str, Any]) -> Venue | None:
    location = raw.get("location")
    if not (isinstance(location, (list, tuple)) and len(location) == 2):
        return None
    lon, lat = location  # Wolt returns GeoJSON order: [lon, lat]
    rating = raw.get("rating") or {}
    score = rating.get("score")
    return Venue(
        id=str(raw.get("id") or raw.get("slug")),
        slug=raw.get("slug", ""),
        name=raw.get("name", "?"),
        lat=float(lat),
        lon=float(lon),
        score=float(score) if score is not None else None,
        online=bool(raw.get("online", False)),
        delivers=bool(raw.get("delivers", False)),
        estimate_range=raw.get("estimate_range"),
        delivery_price=raw.get("delivery_price"),
        price_range=raw.get("price_range"),
        tags=tuple(raw.get("tags") or ()),
        description=raw.get("short_description") or "",
        address=raw.get("address") or "",
        city=raw.get("city") or "",
        country=raw.get("country") or "",
    )


def parse_venues(page: dict[str, Any]) -> list[Venue]:
    """Extract unique venues from a /v1/pages/restaurants response."""
    venues: dict[str, Venue] = {}
    for section in page.get("sections") or ():
        for item in section.get("items") or ():
            raw = item.get("venue")
            if not raw:
                continue
            venue = _parse_venue(raw)
            if venue and venue.id not in venues:
                venues[venue.id] = venue
    return list(venues.values())


class WoltClient:
    def __init__(self, session: requests.Session | None = None, language: str = "ru", timeout: float = 15):
        self.http = session or requests.Session()
        self.http.headers.update({"User-Agent": USER_AGENT, "Accept-Language": language})
        self.timeout = timeout

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        try:
            resp = self.http.get(f"{API_BASE}{path}", params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WoltError(f"Запрос к Wolt не удался: {exc}") from exc
        return resp.json()

    def restaurants_page(self, lat: float, lon: float) -> dict[str, Any]:
        return self._get("/v1/pages/restaurants", lat=lat, lon=lon)

    def venues_near(self, lat: float, lon: float) -> list[Venue]:
        return parse_venues(self.restaurants_page(lat, lon))
