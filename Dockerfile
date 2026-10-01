FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .

ARG UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG UV_INDEX_STRATEGY=unsafe-best-match

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=120
ENV UV_LINK_MODE=copy
ENV UV_INDEX_URL=${UV_INDEX_URL}
ENV UV_INDEX_STRATEGY=${UV_INDEX_STRATEGY}

RUN uv venv /opt/venv && \
    UV_PROJECT_ENVIRONMENT=/opt/venv uv pip install --no-cache --python /opt/venv/bin/python -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

COPY /src /app/src

ENTRYPOINT ["python3", "/app/src/main.py"]