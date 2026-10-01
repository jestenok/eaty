"""The beginner's guide (/guide) and the extension it hands out (/extension.zip). No database:
neither page touches it."""

import io
import json
import re
import zipfile
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "static"
EXTENSION = ROOT / "extension"


def site():
    from config import AppConfig
    from core.db import Database
    from server import create_app

    app = create_app(AppConfig(), database=Database("postgresql+asyncpg://nobody@127.0.0.1:1/none"))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_extension_zip_is_what_load_unpacked_wants():
    from server import extension_zip

    archive = zipfile.ZipFile(io.BytesIO(extension_zip(EXTENSION)))
    names = set(archive.namelist())
    manifest = json.loads(archive.read("manifest.json"))   # at the root, not in a folder
    assert manifest == json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    needed = {manifest["background"]["service_worker"], manifest["action"]["default_popup"],
              *manifest["icons"].values(), *manifest["action"]["default_icon"].values(),
              *(js for script in manifest["content_scripts"] for js in script["js"])}
    assert needed <= names
    assert names == {p.relative_to(EXTENSION).as_posix() for p in EXTENSION.rglob("*") if p.is_file()}


def test_guide_points_to_existing_files():
    html = (STATIC / "guide.html").read_text(encoding="utf-8")
    for rel in re.findall(r'(?:href|src)="/static/([^"]+)"', html):
        assert (STATIC / rel).is_file(), rel
    assert 'href="/extension.zip"' in html
    for anchor in re.findall(r'href="/guide#([\w-]+)"', (STATIC / "app.js").read_text(encoding="utf-8")):
        assert f'id="{anchor}"' in html, anchor


async def test_guide_and_download_need_no_sign_in():
    async with site() as http:
        guide = await http.get("/guide")
        assert guide.status_code == 200 and "Как подключить eaty" in guide.text
        assert guide.headers["cache-control"] == "no-cache"   # an updated guide shows up at once

        download = await http.get("/extension.zip")
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        assert 'filename="eaty-extension.zip"' in download.headers["content-disposition"]
        assert "manifest.json" in zipfile.ZipFile(io.BytesIO(download.content)).namelist()
