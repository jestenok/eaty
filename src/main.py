"""Container entrypoint: `python3 /app/src/main.py` (see Dockerfile).

Same as the `eaty-web` command, but listens on all interfaces by default, because
inside a container 127.0.0.1 is unreachable from outside. Settings come from the
environment: POSTGRES_URI / EATY_DB_NAME or EATY_DATABASE_URL, EATY_PORT (8000).
"""

import os

from eaty.web.app import main

if __name__ == "__main__":
    os.environ.setdefault("EATY_HOST", "0.0.0.0")
    raise SystemExit(main())
