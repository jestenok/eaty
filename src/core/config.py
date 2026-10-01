"""Base settings every service has: environment, HTTP, database server."""

import logging
import os
from enum import Enum


class EnvironmentType(str, Enum):
    PRODUCTION = "prod"
    TEST = "test"
    DEV = "dev"
    LOCAL = "local"


class Config:
    def __init__(self):
        self.PROJECT_NAME = "noname"
        self.API_VERSION = "v1"
        self.API_PREFIX = f"/api/{self.API_VERSION}"
        self.RELEASE_VERSION = "0.1.0"

        # Without ENV the service behaves like production: that's what the Docker image runs.
        self.ENVIRONMENT = EnvironmentType(os.getenv("ENV", EnvironmentType.PRODUCTION.value))
        is_local = self.ENVIRONMENT is EnvironmentType.LOCAL
        # Locally only this computer; in a container 127.0.0.1 is unreachable from outside.
        self.HOST = os.getenv("HOST", "127.0.0.1" if is_local else "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8080"))   # the cluster chart (ingres.port) expects 8080
        self.RELOAD = is_local

        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.ECHO_SQL = os.getenv("ECHO_SQL", "false").lower() == "true"
        self.LOG_LEVEL = logging.DEBUG if self.DEBUG else logging.INFO

        # Database server without the database name: postgresql+asyncpg://user:password@host:port
        self.POSTGRES_URI = os.getenv("POSTGRES_URI")
