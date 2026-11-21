FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM python:3.12-slim-bookworm

COPY --from=uv /uv /uvx /bin/
WORKDIR /workspace/apps/backend
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/backend/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev \
    && groupadd --system cekrir \
    && useradd --system --gid cekrir --no-create-home cekrir

USER cekrir
EXPOSE 8000
CMD ["uvicorn", "cekrir.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
