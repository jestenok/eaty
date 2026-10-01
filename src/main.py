"""Entrypoint: `python src/main.py` locally, `python3 /app/src/main.py` in Docker."""

from pathlib import Path

import uvicorn

from config import get_config


def main() -> None:
    config = get_config()
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"

    uvicorn.run(
        "server:create_app",
        factory=True,              # no app object at import time: config is read when it starts
        app_dir=str(Path(__file__).resolve().parent),
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        workers=1,                 # the catalog refresh job keeps its state in memory
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
