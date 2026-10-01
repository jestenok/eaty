"""Choosing where to order from."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Sequence

from cli.geo import haversine_km
from app.clients.wolt_venues import Venue


@dataclass(frozen=True)
class Candidate:
    venue: Venue
    distance_km: float


def find_candidates(
    venues: Iterable[Venue],
    lat: float,
    lon: float,
    radius_km: float = 1.0,
    min_score: float = 9.0,
    only_open: bool = True,
    tags: Sequence[str] = (),
) -> list[Candidate]:
    """Venues within radius_km of (lat, lon) rated at least min_score, best first."""
    wanted = [t.lower() for t in tags]
    result = []
    for venue in venues:
        if venue.score is None or venue.score < min_score:
            continue
        if only_open and not venue.is_open:
            continue
        if wanted:
            haystack = " ".join((*venue.tags, venue.description, venue.name)).lower()
            if not any(t in haystack for t in wanted):
                continue
        distance = haversine_km(lat, lon, venue.lat, venue.lon)
        if distance <= radius_km:
            result.append(Candidate(venue, distance))
    result.sort(key=lambda c: (-c.venue.score, c.distance_km))
    return result


def pick(candidates: Sequence[Candidate], surprise: bool = False, top: int = 5, rng: random.Random | None = None) -> Candidate | None:
    """Best candidate, or a random one among the top few when surprise is set."""
    if not candidates:
        return None
    if not surprise:
        return candidates[0]
    return (rng or random).choice(candidates[:top])
