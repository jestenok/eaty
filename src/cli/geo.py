"""Distances and address geocoding."""

from __future__ import annotations

import math

import requests

EARTH_RADIUS_KM = 6371.0088
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "eaty/0.1 (personal food picker)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class GeocodeError(RuntimeError):
    pass


def geocode(address: str, session: requests.Session | None = None, timeout: float = 15) -> tuple[float, float]:
    """Resolve a free-form address to (lat, lon) via OpenStreetMap Nominatim."""
    http = session or requests.Session()
    resp = http.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise GeocodeError(f"Адрес не найден: {address!r}")
    return float(results[0]["lat"]), float(results[0]["lon"])
