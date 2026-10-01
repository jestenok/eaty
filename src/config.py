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
