# PostgreSQL and Prisma

Prisma 7 manages the canonical schema and migrations. FastAPI uses psycopg 3 and `psycopg_pool` for runtime queries, keeping the backend in Python. There is no generated Prisma JavaScript client or unsupported Python Prisma client in this architecture.

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

`compose.yaml` starts PostgreSQL 17 on `127.0.0.1:5432` with development-only credentials and a named data volume. It creates `cekrir` for the application and `cekrir_test` for tests. The test database initialization SQL runs only when the volume is new. If the volume predates that initialization, create the missing test database with:

```sh
docker compose exec postgres createdb -U cekrir cekrir_test
```

`pnpm run db:down` stops containers without deleting the data volume. Starting PostgreSQL preserves existing data. Review migration SQL before applying it. Avoid `docker compose down -v` unless you intend to erase the local databases.

For an existing PostgreSQL instance, skip Compose, create separate application/test databases, and configure their URLs in the root `.env`. Use plain PostgreSQL URLs accepted by both Prisma and libpq; omit Prisma-specific parameters such as `schema`. PostgreSQL's default `public` schema is used. Configure TLS using standard PostgreSQL connection parameters for remote servers.

The root `DATABASE_URL` is read by Prisma and FastAPI. Backend-specific settings remain in `apps/backend/.env`; the root dev command handles its working directory. Environment variables override dotenv files. Never put database credentials in frontend `VITE_` variables.

## Change the schema

Edit `prisma/schema.prisma`, then run:

```sh
pnpm run db:migrate --name describe_the_change
pnpm run db:validate
pnpm run check
pnpm test
```

Review and commit the schema and generated migration SQL together. `migrate dev` uses a shadow database, so the development role needs database-creation privileges (the local Compose role has them). For managed databases, configure an appropriate development/shadow database workflow before using `migrate dev`.

Deploy committed migrations with `pnpm run db:deploy` before starting the API. Run migrations once per release, rather than from every API process. The deployment role needs the required DDL permissions; the API runtime role can use narrower read/write permissions.

Database column names use snake case through Prisma `@map` annotations. Python's parameterized SQL in `apps/backend/src/cekrir/repository.py` uses those mapped names. When changing fields, update the queries and Pydantic API contracts alongside the Prisma migration.

The initial migration includes the unique courier/resi pair, shipment status/source enums, JSONB history, UUID defaults, notification foreign key, timezone-aware timestamps, and indexes. Python does not duplicate the database schema through an ORM.

## Run integration tests

```sh
pnpm run db:up
pnpm test
```

The backend test command first deploys Prisma migrations to `TEST_DATABASE_URL`. API tests then connect to real PostgreSQL and clear the `shipment` and `notification` tables between tests. Use a dedicated database whose name ends in `_test`; both the migration wrapper and test fixtures reject using the application's database. Run this suite serially. Never point the test URL at a database containing data you need to keep.

Tests cover concurrent detection registration, simultaneous status refreshes, persistence across application restarts, JSONB/timestamp round trips, foreign keys, and transactional rollback when notification insertion fails. GitHub Actions supplies a PostgreSQL service and applies the same migrations before running tests.

The earlier SQLite development files are left untouched. They are no longer read by the API, and their contents are not automatically imported into PostgreSQL.
