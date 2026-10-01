import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.dependencies import catalog_service_factory
from api.routers import router as api_router
from app.clients.wolt_catalog import WoltCatalogClient
from app.service.catalog import CatalogRefreshJob
from config import AppConfig, get_config
from core.db import Database
from core.db.migrations import upgrade_to_head
from core.error.handlers import register_exception_handlers
from core.fastapi.middlewares import RevalidateStaticMiddleware

SRC = Path(__file__).resolve().parent
STATIC = SRC / "static"
MIGRATIONS = SRC / "migrations"


def setup_logging(config: AppConfig) -> None:
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s", force=True)


def create_app(config: AppConfig | None = None, database: Database | None = None) -> FastAPI:
    """App factory: nothing is created at import time, everything the app needs lives
    in app.state and reaches handlers through Depends (see api/dependencies.py)."""
    config = config or get_config()
    database = database or Database(config.DATABASE_URL, echo=config.ECHO_SQL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if config.MIGRATE_ON_START:
            await upgrade_to_head(database, MIGRATIONS)

        catalog_client = WoltCatalogClient(language=config.WOLT_LANGUAGE)
        app.state.catalog_job = CatalogRefreshJob(
            database, catalog_service_factory(catalog_client), pause=config.CATALOG_PAUSE_SECONDS)
        yield
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
    app.add_middleware(RevalidateStaticMiddleware)
    app.include_router(api_router, prefix="/api")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    return app
