"""Pack sizes from Wolt labels ("500 г", "1 кг", "15 шт", "1 л") in base units."""

from __future__ import annotations

import re

_AMOUNT = re.compile(r"~?\s*(\d+(?:[.,]\d+)?)\s*(кг|гр|г|мл|л|шт)(?![а-яёa-z])", re.IGNORECASE)
_TO_BASE = {"кг": (1000, "g"), "гр": (1, "g"), "г": (1, "g"), "л": (1000, "ml"), "мл": (1, "ml"), "шт": (1, "pcs")}


def parse_amount(text: str | None) -> tuple[float, str] | None:
    """'500 г' -> (500, 'g'); '1,5 кг' -> (1500, 'g'); '15 шт' -> (15, 'pcs'). Last match wins,
    so 'Рис 800 г' and 'Банан, 1 кг' both work."""
    if not text:
        return None
    matches = _AMOUNT.findall(text)
    if not matches:
        return None
    number, unit = matches[-1]
    factor, base = _TO_BASE[unit.lower()]
    return float(number.replace(",", ".")) * factor, base


def format_amount(amount: float, unit: str) -> str:
    """600 g -> '600 г', 1200 g -> '1,2 кг', 5 pcs -> '5 шт'."""
    if unit == "pcs":
        return f"{amount:g} шт"
    big, small = ("кг", "г") if unit == "g" else ("л", "мл")
    if amount >= 1000:
        return f"{amount / 1000:.2f}".rstrip("0").rstrip(".").replace(".", ",") + f" {big}"
    return f"{amount:.0f} {small}"
