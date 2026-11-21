# PostgreSQL, SQLAlchemy, and Alembic

SQLAlchemy models define the backend data structures in `apps/backend/src/cekrir/db/model`. Alembic owns versioned schema migrations in `apps/backend/migrations`. PostgreSQL is the durable store; Redis is used for live notification fanout.

## Local setup

From the repository root:

```sh
cp .env.example .env
pnpm install --frozen-lockfile
uv sync --project apps/backend --frozen
pnpm run db:deploy
pnpm run dev
```

`compose.yaml` is the VM deployment configuration described in the [Ubuntu VM guide](ubuntu-vm-setup.md). Its PostgreSQL and Redis services are private to Docker and it creates the application database only. The VM stack uses the `vm_postgres_data` named volume; an older local `postgres_data` volume is separate and is not automatically migrated or deleted.

For an existing PostgreSQL instance, create separate application and test databases and configure `DATABASE_URL` and `TEST_DATABASE_URL` in the root `.env`. The backend also reads `apps/backend/.env`; if both files set `DATABASE_URL`, the backend file wins for both the API and Alembic, regardless of the working directory. Values provided as process environment variables take precedence over both. Password characters with special meaning in a URL, such as `@`, `:`, `/`, or `%`, must be percent-encoded. Keep the application and test database URLs different. The initial Alembic migration creates missing shipment and notification tables, recognizes the existing Prisma-created versions, and adds the authentication user table. It does not modify or delete existing shipment data.

After configuring `DATABASE_URL`, set `CEKRIR_SEED_ADMIN_PASSWORD` and `CEKRIR_SEED_MEMBER_PASSWORD` in the process environment or in the private, Git-ignored `apps/backend/.env.seed` file. If the bootstrap admin password is set, it can also supply the seed admin password. Passwords are required when an account needs to be created, and must be at least 12 characters and at most 72 UTF-8 bytes. Existing accounts and passwords are preserved. On Windows, double-click `apps/backend/migrate_and_seed.bat` to apply the migrations, including the seed migration.

You can also run Alembic from the repository root:

```powershell
& apps/backend/.venv/Scripts/python.exe -m alembic -c apps/backend/alembic.ini upgrade head
```

The data migration `20261120_0007` creates an admin, member, and admin-owned location. The admin email defaults to `CEKRIR_BOOTSTRAP_ADMIN_EMAIL` when configured, or `admin@example.test`; the member and location default to `member@example.test` and `Main Location`. Override these before the migration using `CEKRIR_SEED_ADMIN_EMAIL`, `CEKRIR_SEED_MEMBER_EMAIL`, and `CEKRIR_SEED_LOCATION`. The migration marks newly created seed accounts verified; the example addresses are not real mailboxes, so configure appropriate values before running it outside local development. It fails on role conflicts and requires an online PostgreSQL connection. Alembic applies the revision only once per database, so changing seed settings afterwards does not rerun it. Downgrading the revision leaves the accounts and location in place because they may already have existed or contain user data.

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
pnpm test
```

The backend test command applies Alembic migrations to `TEST_DATABASE_URL`. Tests require a separately created PostgreSQL database whose name ends in `_test`, distinct from `DATABASE_URL`, and truncate shipment and notification rows between cases. The VM Compose setup does not create or expose a test database.

The migration is compatible with the prior schema: when applied to a database created by the old Prisma migration, it records the Alembic baseline and adds only missing structures. For a clean database it creates all current tables. Back up persistent data before applying any future migration that changes or removes columns.
