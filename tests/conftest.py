import pytest

# Delivery point used across tests (central Tbilisi).
HOME = (41.7000, 44.8000)


def venue(id, name, lat, lon, score=9.2, online=True, delivers=True, tags=("burger",), **extra):
    raw = {
        "id": id,
        "slug": f"{id}-slug",
        "name": name,
        "location": [lon, lat],
        "online": online,
        "delivers": delivers,
        "estimate_range": "25-35",
        "delivery_price": "₾2.99",
        "price_range": 2,
        "tags": list(tags),
        "short_description": "",
        "address": "Some st. 1",
        "city": "Tbilisi",
        "country": "GEO",
        **extra,
    }
    if score is not None:
        raw["rating"] = {"rating": 4, "score": score}
    return raw


@pytest.fixture
def page():
    """Shape of GET consumer-api.wolt.com/v1/pages/restaurants."""
    near_best = venue("a", "Near Best", 41.7030, 44.8000, score=9.6)          # ~330 m
    return {
        "name": "restaurants",
        "sections": [
            {
                "name": "popular",
                "items": [{"title": "Near Best", "venue": near_best}],
            },
            {
                "name": "restaurants-delivering-venues",
                "items": [
                    {"title": "Near Best", "venue": near_best},  # duplicate across sections
                    {"venue": venue("b", "Near Good", 41.7050, 44.8000, score=9.1, tags=("sushi",))},  # ~560 m
                    {"venue": venue("c", "Near Meh", 41.7010, 44.8000, score=8.2)},   # ~110 m, low score
                    {"venue": venue("d", "Far Great", 41.7200, 44.8000, score=9.8)},  # ~2.2 km
                    {"venue": venue("e", "Near Closed", 41.7020, 44.8000, score=9.7, online=False)},
                    {"venue": venue("f", "Near Unrated", 41.7020, 44.8000, score=None)},
                    {"venue": venue("g", "No Location", 0, 0, location=None)},
                    {"title": "banner without venue"},
                ],
            },
        ],
    }
