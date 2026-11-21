# One shared image for three separate containers: PostgreSQL, Redis, and the API.
# Keep the PostgreSQL major version and Alpine image family used by the VM volume.
FROM redis:7-alpine AS redis
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM postgres:17-alpine AS base

# Apply available Alpine security updates when the image is built.
RUN apk upgrade --no-cache \
    && apk add --no-cache python3 ca-certificates libstdc++ libgcc \
    && addgroup -S cekrir \
    && adduser -S -D -H -G cekrir cekrir
COPY --from=redis /usr/local/bin/redis-server /usr/local/bin/redis-server
COPY --from=redis /usr/local/bin/redis-cli /usr/local/bin/redis-cli

WORKDIR /workspace/apps/backend
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/backend/.venv/bin:$PATH"

FROM base AS builder
COPY --from=uv /uv /uvx /bin/
# zxing-cpp has no locked musllinux wheel and is compiled for Alpine.
RUN apk add --no-cache build-base cmake ninja python3-dev linux-headers
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

FROM base AS runtime
COPY --from=builder /workspace/apps/backend /workspace/apps/backend
# The official PostgreSQL entrypoint creates this user and database on the first
# start of an empty volume. POSTGRES_PASSWORD must be supplied at runtime.
ENV POSTGRES_USER=cekrir \
    POSTGRES_DB=cekrir
# Fail the build if any executable or required shared library is missing.
RUN postgres --version \
    && redis-server --version \
    && redis-cli --version \
    && python -c "import alembic, bcrypt, cekrir.main, psycopg, redis, zxingcpp"

# Retain the official PostgreSQL entrypoint and default. Compose overrides the
# command and user for Redis and the API, while the db service runs PostgreSQL.
CMD ["postgres"]
