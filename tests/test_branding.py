"""The logo files the site, its web manifest and the extension point to exist, at the sizes they claim."""

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "static"


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def test_site_head_points_to_existing_files():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    paths = re.findall(r'href="/static/([^"]+)"', html)
    assert {"favicon.svg", "icons/apple-touch-icon.png", "manifest.webmanifest"} <= set(paths)
    for rel in paths:
        assert (STATIC / rel).is_file(), rel
    assert (STATIC / "favicon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"  # served at /favicon.ico
    assert png_size(STATIC / "icons" / "apple-touch-icon.png") == (180, 180)
    assert png_size(STATIC / "og.png") == (1200, 630)


def test_web_manifest_icons():
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    for icon in manifest["icons"]:
        width, height = map(int, icon["sizes"].split("x"))
        assert png_size(STATIC / icon["src"].removeprefix("/static/")) == (width, height)


def test_extension_icons():
    manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    for icons in (manifest["icons"], manifest["action"]["default_icon"]):
        for size, rel in icons.items():
            assert png_size(ROOT / "extension" / rel) == (int(size), int(size))
