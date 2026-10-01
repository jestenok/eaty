import re


def matches(name: str, match_re: str, exclude_re: str) -> bool:
    """Does a Wolt item name count as the product: fits `match_re` and not `exclude_re`."""
    return bool(re.search(match_re, name, re.IGNORECASE)) and not (
        exclude_re and re.search(exclude_re, name, re.IGNORECASE)
    )
