# PostgreSQL, SQLAlchemy, and Alembic

SQLAlchemy models define the backend data structures in `apps/backend/src/cekrir/db/model`. Alembic owns versioned schema migrations in `apps/backend/migrations`. PostgreSQL is the durable store; Redis is used for live notification fanout.

## Local setup

From the repository root:

```sh
cp .env.example .env
pnpm install --frozen-lockfile
uv sync --project apps/backend --frozen
pnpm run db:up
pnpm run db:deploy
pnpm run dev
```

`compose.yaml` starts PostgreSQL 17 and Redis 7 on loopback addresses. PostgreSQL uses a development-only credential and named volume. It creates the `cekrir` application database and `cekrir_test` test database. `pnpm run db:down` stops the containers without deleting the volume.

For an existing PostgreSQL instance, create separate application and test databases and configure `DATABASE_URL` and `TEST_DATABASE_URL` in the root `.env`. The initial Alembic migration creates missing shipment and notification tables, recognizes the existing Prisma-created versions, and adds the authentication user table. It does not modify or delete existing shipment data.

The API uses SQLAlchemy's synchronous ORM session with the psycopg 3 driver. Each request receives a short-lived session; migrations run as a separate deployment command and are not applied by every API worker. Never place database credentials in frontend `VITE_` variables.

## Change the schema

Edit the modular SQLAlchemy models, exported by `apps/backend/src/cekrir/db/model/__init__.py`, then generate a candidate migration:

```sh
pnpm run db:migrate -- -m "describe the change"
```

Review the generated Python migration and adjust it for data migration or PostgreSQL-specific behavior. Then apply and compare the schema:

```sh
pnpm run db:deploy
pnpm run db:validate
```

Alembic autogenerate produces a candidate based on model metadata; it does not replace review. Commit model changes and their Alembic revision together. Existing files under `prisma/` are retained for historical reference and must not be used for new migrations.

## Test database

```sh
pnpm run db:up
pnpm test
```

The backend test command applies Alembic migrations to `TEST_DATABASE_URL`. Tests require a PostgreSQL database whose name ends in `_test`, distinct from `DATABASE_URL`, and truncate shipment and notification rows between cases. The Compose initialization script creates `cekrir_test` on the first volume initialization.

The migration is compatible with the prior schema: when applied to a database created by the old Prisma migration, it records the Alembic baseline and adds only missing structures. For a clean database it creates all current tables. Back up persistent data before applying any future migration that changes or removes columns.
