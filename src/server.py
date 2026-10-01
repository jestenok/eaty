import io
import logging
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from mcp.server.transport_security import TransportSecuritySettings

from api.dependencies import catalog_service_factory
from api.mcp.consent import router as consent_router
from api.mcp.server import MCP_PATH, build_mcp, mcp_routes
from api.routers import router as api_router
from app.clients.web_push import WebPushClient
from app.clients.wolt_catalog import WoltCatalogClient
from app.service.catalog import CatalogRefreshJob
from app.service.push import TimerPushJob, load_push_key
from config import AppConfig, get_config
from core.db import Database
from core.db.migrations import upgrade_to_head
from core.error import NotFoundError
from core.error.handlers import register_exception_handlers
from core.fastapi.middlewares import RevalidateStaticMiddleware

SRC = Path(__file__).resolve().parent
STATIC = SRC / "static"
MIGRATIONS = SRC / "migrations"
EXTENSION = SRC.parent / "extension"   # in Docker: /app/extension next to /app/src


def setup_logging(config: AppConfig) -> None:
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s", force=True)


def extension_zip(folder: Path) -> bytes:
    """The Chrome extension as a zip with manifest.json at the root: "Extract all" gives the very
    folder that chrome://extensions → "Load unpacked" wants."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and not any(part.startswith(".") for part in path.relative_to(folder).parts):
                archive.write(path, path.relative_to(folder).as_posix())
    return buffer.getvalue()


def create_app(config: AppConfig | None = None, database: Database | None = None) -> FastAPI:
    """App factory: nothing is created at import time, everything the app needs lives
    in app.state and reaches handlers through Depends (see api/dependencies.py)."""
    config = config or get_config()
    database = database or Database(config.DATABASE_URL, echo=config.ECHO_SQL)
    mcp = build_mcp(config, database)
    # Stateless JSON: every MCP request stands alone, so restarts and deploys drop nothing. No DNS
    # rebinding check: it guards servers without auth on localhost, and this one needs a token.
    mcp_app = mcp.streamable_http_app(
        streamable_http_path=MCP_PATH, stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if config.MIGRATE_ON_START:
            await upgrade_to_head(database, MIGRATIONS)

        catalog_client = WoltCatalogClient(language=config.WOLT_LANGUAGE)
        app.state.catalog_job = CatalogRefreshJob(
            database, catalog_service_factory(catalog_client), pause=config.CATALOG_PAUSE_SECONDS)
        push_key = await load_push_key(database)
        push_client = WebPushClient(push_key.private_key, contact=config.PUSH_CONTACT)
        app.state.push_public_key = push_key.public_key
        app.state.push_job = TimerPushJob(database, push_client.send, poll=config.PUSH_POLL_SECONDS)
        app.state.push_job.start()
        async with mcp.session_manager.run():  # the MCP app's own lifespan: we only took its routes
            yield
        await app.state.push_job.stop()
        await push_client.aclose()
        await app.state.catalog_job.stop()
        await catalog_client.aclose()
        await database.dispose()

    app = FastAPI(
        title=config.PROJECT_NAME.capitalize(),
        version=config.RELEASE_VERSION,
        openapi_url=f"{config.API_PREFIX}/openapi.json",
        docs_url=f"{config.API_PREFIX}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.db = database

    setup_logging(config)
    register_exception_handlers(app)
    app.add_middleware(RevalidateStaticMiddleware, prefixes=("/static/", "/guide"))
    app.include_router(api_router, prefix="/api")
    app.include_router(consent_router)
    app.router.routes.extend(mcp_routes(mcp_app))
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():  # browsers and link previews ask for it at the root
        return FileResponse(STATIC / "favicon.ico", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():  # at the root, so it may serve the whole app (it shows the timer pushes)
        return FileResponse(STATIC / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})

    @app.get("/guide", include_in_schema=False)
    async def guide():  # how to connect the extension and Claude; open without signing in
        return FileResponse(STATIC / "guide.html")

    @app.get("/extension.zip", include_in_schema=False)
    async def extension_download():
        if not (EXTENSION / "manifest.json").is_file():
            raise NotFoundError("Расширения нет рядом с приложением")
        return Response(extension_zip(EXTENSION), media_type="application/zip", headers={
            "Content-Disposition": 'attachment; filename="eaty-extension.zip"', "Cache-Control": "no-cache"})

    return app
