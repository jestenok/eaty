"""Command line: `eaty` / `python -m eaty`."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from cli.settings import Settings, load_dotenv
from cli.geo import GeocodeError, geocode
from cli.picker import Candidate, find_candidates, pick
from app.clients.wolt_venues import WoltClient, WoltError, parse_venues


def build_parser(settings: Settings) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m cli", description="Что заказать в Wolt: рестораны рядом с хорошим рейтингом.")
    p.add_argument("--lat", type=float, default=settings.lat, help="широта точки доставки (EATY_LAT)")
    p.add_argument("--lon", type=float, default=settings.lon, help="долгота точки доставки (EATY_LON)")
    p.add_argument("--address", default=settings.address, help="адрес вместо координат (EATY_ADDRESS)")
    p.add_argument("--radius", type=float, default=settings.radius_km, help="макс. расстояние до ресторана, км (по умолчанию %(default)s)")
    p.add_argument("--min-score", type=float, default=settings.min_score, help="мин. рейтинг Wolt по шкале 0-10 (по умолчанию %(default)s)")
    p.add_argument("--tag", action="append", default=[], help="кухня или блюдо, напр. --tag sushi --tag pizza")
    p.add_argument("--include-closed", action="store_true", help="показывать и закрытые сейчас рестораны")
    p.add_argument("--limit", type=int, default=10, help="сколько ресторанов показать (по умолчанию %(default)s)")
    p.add_argument("--surprise", action="store_true", help="выбрать случайный из топ-5, а не лучший")
    p.add_argument("--json", action="store_true", help="вывести результат в JSON")
    p.add_argument("--from-file", type=Path, help="взять ответ Wolt из сохранённого JSON вместо запроса")
    return p


def resolve_location(args: argparse.Namespace) -> tuple[float, float]:
    if args.lat is not None and args.lon is not None:
        return args.lat, args.lon
    if args.address:
        return geocode(args.address)
    raise SystemExit("Не знаю, куда доставлять: укажи --lat/--lon или --address (или EATY_LAT/EATY_LON в .env).")


def format_candidate(n: int, c: Candidate) -> str:
    v = c.venue
    parts = [f"{v.score:.1f}★", f"{c.distance_km * 1000:.0f} м"]
    if v.estimate_range:
        parts.append(f"{v.estimate_range} мин")
    if v.delivery_price:
        parts.append(f"доставка {v.delivery_price}")
    if v.price_range:
        parts.append("$" * v.price_range)
    lines = [f"{n:>2}. {v.name} — " + " · ".join(parts)]
    about = v.description or ", ".join(v.tags)
    if about:
        lines.append(f"    {about}")
    lines.append(f"    {v.url()}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser(Settings.from_env()).parse_args(argv)

    try:
        lat, lon = resolve_location(args)
        if args.from_file:
            venues = parse_venues(json.loads(args.from_file.read_text(encoding="utf-8")))
        else:
            venues = WoltClient().venues_near(lat, lon)
    except (WoltError, GeocodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    candidates = find_candidates(
        venues, lat, lon,
        radius_km=args.radius,
        min_score=args.min_score,
        only_open=not args.include_closed,
        tags=args.tag,
    )
    choice = pick(candidates, surprise=args.surprise)

    if args.json:
        payload = {
            "location": {"lat": lat, "lon": lon},
            "choice": asdict(choice) if choice else None,
            "candidates": [asdict(c) for c in candidates[: args.limit]],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Точка: {lat:.5f}, {lon:.5f} · радиус {args.radius:g} км · рейтинг от {args.min_score:g}")
    print(f"Wolt вернул {len(venues)} ресторанов, подходят {len(candidates)}.\n")
    if not choice:
        print("Ничего не нашлось. Попробуй --min-score 8.5, --radius 1.5 или --include-closed.")
        return 0
    for n, c in enumerate(candidates[: args.limit], 1):
        print(format_candidate(n, c))
    print(f"\nРекомендую: {choice.venue.name} ({choice.venue.score:.1f}★, {choice.distance_km * 1000:.0f} м)")
    return 0
