import json
import random

import pytest

from eaty.cli import main
from eaty.geo import haversine_km
from eaty.picker import find_candidates, pick
from eaty.wolt import parse_venues

from conftest import HOME


def test_haversine_known_distance():
    # Helsinki -> Tallinn is about 82 km in a straight line.
    assert haversine_km(60.1699, 24.9384, 59.4370, 24.7536) == pytest.approx(82, abs=2)
    assert haversine_km(*HOME, *HOME) == 0


def test_parse_venues_dedupes_and_skips_bad_items(page):
    venues = parse_venues(page)
    names = [v.name for v in venues]
    assert names == ["Near Best", "Near Good", "Near Meh", "Far Great", "Near Closed", "Near Unrated"]
    best = venues[0]
    assert (best.lat, best.lon) == (41.7030, 44.8000)
    assert best.score == 9.6
    assert venues[-1].score is None


def test_venue_url(page):
    best = parse_venues(page)[0]
    assert best.url() == "https://wolt.com/ru/geo/tbilisi/restaurant/a-slug"


def test_find_candidates_filters_radius_score_and_open(page):
    found = find_candidates(parse_venues(page), *HOME, radius_km=1.0, min_score=9.0)
    assert [c.venue.name for c in found] == ["Near Best", "Near Good"]
    assert found[0].distance_km == pytest.approx(0.33, abs=0.01)


def test_find_candidates_include_closed_and_lower_score(page):
    found = find_candidates(parse_venues(page), *HOME, min_score=8.0, only_open=False)
    assert [c.venue.name for c in found] == ["Near Closed", "Near Best", "Near Good", "Near Meh"]


def test_find_candidates_by_tag(page):
    found = find_candidates(parse_venues(page), *HOME, tags=["SUSHI"])
    assert [c.venue.name for c in found] == ["Near Good"]


def test_pick(page):
    found = find_candidates(parse_venues(page), *HOME)
    assert pick(found).venue.name == "Near Best"
    assert pick(found, surprise=True, rng=random.Random(1)) in found
    assert pick([]) is None


def test_cli_from_file(tmp_path, page, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no stray .env
    saved = tmp_path / "page.json"
    saved.write_text(json.dumps(page), encoding="utf-8")

    assert main(["--lat", str(HOME[0]), "--lon", str(HOME[1]), "--from-file", str(saved)]) == 0
    out = capsys.readouterr().out
    assert "подходят 2" in out
    assert "Рекомендую: Near Best (9.6★, 334 м)" in out

    assert main(["--lat", str(HOME[0]), "--lon", str(HOME[1]), "--from-file", str(saved), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["choice"]["venue"]["name"] == "Near Best"
    assert len(data["candidates"]) == 2


def test_cli_requires_location(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("EATY_LAT", "EATY_LON", "EATY_ADDRESS"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit, match="Не знаю, куда доставлять"):
        main([])
