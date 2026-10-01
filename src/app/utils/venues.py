import re
from typing import Literal

VenueKind = Literal["store", "restaurant", "unknown"]


def venue_kind(*, product_line: str | None, venue_url: str | None, venue_name: str | None,
               grocery_re: str) -> VenueKind:
    """Store or restaurant, by the most reliable sign the order has:
    the venue type Wolt reports, then its wolt.com address (stores live under /venue/,
    restaurants under /restaurant/), then the name against known grocery chains."""
    line = (product_line or "").lower()
    if re.search(r"grocer|retail|store|market|shop|butcher", line):
        return "store"
    if re.search(r"restaurant|food|cafe", line):
        return "restaurant"
    url = venue_url or ""
    if "/venue/" in url:
        return "store"
    if "/restaurant/" in url:
        return "restaurant"
    if venue_name and re.search(grocery_re, venue_name, re.IGNORECASE):
        return "store"
    return "unknown"
