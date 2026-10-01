"""eaty settings. Everything comes from the environment (locally from .env)."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy.engine import URL

import core.config
from core.config import EnvironmentType  # noqa: F401  (re-exported for the app)
from core.db.url import to_async_url
from core.error import ConfigError


class AppConfig(core.config.Config):
    def __init__(self):
        super().__init__()
        self.PROJECT_NAME = "eaty"
        self.RELEASE_VERSION = "0.3.0"

        self.DB_NAME = os.getenv("DB_NAME", "eaty")
        # A full URL wins over POSTGRES_URI + DB_NAME (tests, one-off runs).
        self._DATABASE_URL = os.getenv("DATABASE_URL")
        self.MIGRATE_ON_START = os.getenv("MIGRATE_ON_START", "true").lower() == "true"

        self.WOLT_CITY = os.getenv("WOLT_CITY", "batumi")
        self.WOLT_LANGUAGE = "ru"
        # Pause between catalog searches: Wolt answers 429 when asked too often.
        self.CATALOG_PAUSE_SECONDS = float(os.getenv("CATALOG_PAUSE_SECONDS", "0.6"))
        # How long a sign-in lasts (browser and Chrome extension).
        self.SESSION_DAYS = int(os.getenv("SESSION_DAYS", "180"))

        # Where users and Claude reach the app: the MCP server is {PUBLIC_URL}/mcp, and it is the
        # OAuth issuer, so it must be the real external address (https unless it's localhost).
        self.PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://localhost:{self.PORT}").rstrip("/")
        # Claude's access token to the MCP server; it renews it with a refresh token (SESSION_DAYS).
        self.MCP_ACCESS_TOKEN_HOURS = int(os.getenv("MCP_ACCESS_TOKEN_HOURS", "24"))

        # Orders from Wolt: only grocery stores, only recent ones (older food is long eaten).
        self.ORDERS_MAX_AGE_DAYS = int(os.getenv("ORDERS_MAX_AGE_DAYS", "7"))
        # Fallback when an order doesn't say what kind of venue it came from.
        self.GROCERY_VENUES_RE = os.getenv(
            "GROCERY_VENUES_RE",
            r"wolt market|red market|carrefour|spar|europroduct|magniti|магнит|smart|gastronome|belmart|"
            r"\baria\b|econom|goodwill|nikora|никора|fresco|nabiji|libre|agrohub|zgapari|market|маркет|продукт",
        )

    @property
    def DATABASE_URL(self) -> URL:
        raw = self._DATABASE_URL or self.POSTGRES_URI
        if not raw:
            raise ConfigError("Не задана база: впиши POSTGRES_URI (и DB_NAME) или DATABASE_URL в .env")
        return to_async_url(raw, self.DB_NAME)


@lru_cache
def get_config() -> AppConfig:
    load_dotenv()
    return AppConfig()
