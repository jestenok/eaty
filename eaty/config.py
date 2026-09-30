"""Settings from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader: KEY=VALUE lines; real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _float(name: str) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else None


@dataclass(frozen=True)
class Settings:
    lat: float | None
    lon: float | None
    address: str | None
    radius_km: float
    min_score: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            lat=_float("EATY_LAT"),
            lon=_float("EATY_LON"),
            address=os.environ.get("EATY_ADDRESS") or None,
            radius_km=_float("EATY_RADIUS_KM") or 1.0,
            min_score=_float("EATY_MIN_SCORE") or 9.0,
        )
