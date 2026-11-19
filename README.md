# Cekrir

GitHub-connected frontend deployment: https://cekrir-frontend.vercel.app (also https://cekrir.vercel.app). These URLs describe the previous deployment; the API integration below has been verified locally and has not been deployed. See the [deployment record](docs/frontend/vercel-deployment.md).

A monorepo for a household delivery app. The confirmed target uses proximity-triggered **ESP32 camera images** for Python barcode decoding; the selected **BARDI CCTV** supplies the separate delivery photo. The existing backend and firmware remain scaffold implementations pending alignment.

The active frontend integrates email/password authentication, verification-pending registration, shared shipment records, foreground notifications, and admin role changes. Household isolation, delivery photos, device management, payment screens, and background push remain unavailable. See the [API integration report](docs/frontend/api-integration.md).

Three apps, one repository:

| App             | Stack                                                         | Purpose                                                                |
| --------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `apps/backend`  | Python 3.12+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis | Authenticated detection, tracking, persistence, live notification feed |
| `apps/frontend` | Vue 3, TypeScript, Vite, Capacitor                            | Shipment tracking UI; Android target, native integration unverified    |
| `apps/esp32`    | Arduino C++, PlatformIO                                       | Camera firmware that sends JPEG frames to the barcode detection API    |

The default tracking provider is an explicitly labeled **offline demo**. It never calls a courier API. The HTTP provider and camera worker can be enabled separately. Shipment and notification routes use JWT authentication; camera submissions can use the optional ingestion key. Live notification events use Redis Pub/Sub, while PostgreSQL remains the durable notification store.

## Documentation

- [Product requirements (PRD)](docs/prd.md): scope, decisions, research, and open questions.
- [Backend deployment discussion](docs/backend-deployment.md): laptop, tunnel, and cloud options for team review.
- [Payment preparation](docs/payments.md): idempotent drafts and QRIS integration requirements.
- [Roles, permissions, and locations](docs/roles-locations.md): access checks and location ownership.

These pages were imported from Notion so they can be read and discussed on GitHub. Their planning statuses are preserved; implementation details are documented below and in the existing engineering docs.

## Start locally

Install **Node.js 24 LTS**, pnpm 11, [uv](https://docs.astral.sh/uv/getting-started/installation/), and **Docker with Compose**. uv can install the required Python version. An existing PostgreSQL server can also be used instead of Docker.

```sh
git clone https://github.com/ahmadnaufal-f/cekrir.git
cd cekrir
corepack enable
pnpm install --frozen-lockfile
uv sync --project apps/backend --frozen
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env
pnpm run db:up
pnpm run db:deploy
pnpm run dev
```

- Dashboard: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

To enable admin-only tracking refresh and role management, set both `CEKRIR_BOOTSTRAP_ADMIN_EMAIL` and `CEKRIR_BOOTSTRAP_ADMIN_PASSWORD` in `apps/backend/.env` before the first API start. Configure SMTP for `POST /api/v1/auth/register`; new members confirm their email before signing in. See [authentication and role setup](docs/integrations.md#authentication-and-roles).

The frontend defaults to live mode against `VITE_API_BASE_URL` (development default `/api/v1`). Register a member, confirm the emailed link, and sign in; configure the bootstrap administrator separately. Sessions are memory-only, so page reloads and app restarts require signing in again. To review without a backend, run `VITE_APP_MODE=mock pnpm run dev:frontend` and sign in with `admin@demo.test` or `member@demo.test`, password `demo12345678`. Mock registrations remain verification-pending and do not send email. Production builds exclude mock fixtures. On static hosting, set a reachable HTTPS API URL and configure backend CORS; there is no production `/api` proxy.

Backend demo tracking always reports `in_transit`; it is sample data. PostgreSQL persists in the Compose `postgres_data` volume. The root dev command starts both apps and stops them together with Ctrl+C; `pnpm run db:down` stops PostgreSQL and Redis while preserving the PostgreSQL volume.

**SQLAlchemy owns the backend ORM models and Alembic owns versioned migrations.** The model package is in `apps/backend/src/cekrir/db/model`; run committed migrations with `pnpm run db:deploy`. Existing Prisma migration files are retained as a historical record and are no longer used. See [database setup](docs/database.md) for schema changes, testing, and deployment.

## Try a camera detection without a camera

With the API running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/detections \
  -H 'Content-Type: application/json' \
  -d '{"resi_number":"CEKRIR987654","courier":"jne","camera_id":"front-door"}'
```

This backend detection creates a shipment and feed notification. If `CEKRIR_INGEST_API_KEY` is configured, send the matching `X-Ingest-Key` header; otherwise use an admin bearer token. It populates the shared shipment list and foreground notification feed; it does not deliver remote push. Its permanent courier/resi uniqueness differs from the target household delivery-event deduplication window.

## ESP32 camera scanner

The [ESP32 app](apps/esp32/README.md) includes PlatformIO profiles for **Seeed XIAO ESP32S3 Sense** and **AI Thinker ESP32-CAM**. Start with a camera-equipped board with PSRAM and evaluate its optics with actual shipping labels before buying a batch.

The firmware uploads small JPEG snapshots to `POST /api/v1/detections/frame`. FastAPI decodes Code 128, Code 39, ITF, or direct-resi QR barcodes and reuses shipment tracking and notification deduplication. Decoding runs on the server; frames are processed in memory without being stored. Multiple possible resi codes in one frame are reported as ambiguous and create no shipments.

```sh
cp apps/esp32/include/config.example.h apps/esp32/include/config.h
# Set Wi-Fi, API URL, camera ID, courier, ingestion key, and HTTPS root CA.
pnpm run firmware:build
pnpm run firmware:test
```

See the firmware README for flashing, a trusted LAN development setup, board selection, frame limits, and hardware validation steps.

## Commands

Run these from the repository root:

| Command                                                     | Purpose                                                                 |
| ----------------------------------------------------------- | ----------------------------------------------------------------------- |
| `pnpm run dev`                                              | Run FastAPI and Vite                                                    |
| `pnpm run dev:backend`                                      | Run FastAPI only                                                        |
| `pnpm run dev:frontend`                                     | Run Vite only                                                           |
| `pnpm run check`                                            | Oxfmt, Oxlint, Alembic schema check, Python lint, Vue/TypeScript checks |
| `pnpm test`                                                 | API integration tests and frontend API tests                            |
| `pnpm run build`                                            | Type check and build the frontend                                       |
| `pnpm run format`                                           | Format Python and web/docs/config files                                 |
| `pnpm run db:up`                                            | Start local PostgreSQL and Redis and wait for readiness                 |
| `pnpm run db:down`                                          | Stop local PostgreSQL; keep persisted data                              |
| `pnpm run db:deploy`                                        | Apply committed Alembic migrations                                      |
| `pnpm run db:migrate -- -m "change_name"`                   | Generate an Alembic migration for review                                |
| `pnpm run firmware:build`                                   | Cross-compile the default ESP32S3 camera profile                        |
| `pnpm run firmware:build --environment ai_thinker_esp32cam` | Cross-compile the AI Thinker profile                                    |
| `pnpm run firmware:test`                                    | Run firmware policy tests on the host                                   |
| `pnpm run firmware:upload --environment xiao_esp32s3_sense` | Flash a connected device                                                |
| `pnpm run firmware:monitor`                                 | Open the serial monitor at 115200 baud                                  |

`pnpm test` applies Alembic migrations to `TEST_DATABASE_URL` and runs the API tests against that dedicated PostgreSQL database. Compose creates `cekrir_test` on its first initialization. Tests clear its shipment/notification tables; they require a database name ending in `_test` and reject the application database. Frontend tests do not need PostgreSQL.

Python dependencies live in `apps/backend/pyproject.toml` and `apps/backend/uv.lock`. The frontend is a pnpm workspace defined in `pnpm-workspace.yaml`, with a root `pnpm-lock.yaml`. Commit both lockfiles when dependencies change. CI runs the same checks with frozen dependency installation.

Formatting uses Oxfmt and JavaScript/TypeScript linting uses Oxlint with Vue and Vitest support. See [tooling setup](docs/tooling.md) for versions, editor integration, focused frontend checks, and formatting commands.

## Mobile apps

Capacitor uses `apps/frontend/dist` as its web bundle. See [mobile setup](docs/mobile.md) for Android/iOS configuration, HTTPS API access, and notification limitations.

## Project map

```text
apps/
  backend/
    src/cekrir/
      routers/        # HTTP and WebSocket endpoints
      validation/     # Request models and bounded frame validation
      services/       # Account, detection, shipment and payment workflows
      middleware/     # JWT authentication and role permissions
      db/
        model/        # SQLAlchemy models and model index
        repository.py # SQLAlchemy persistence queries
        session.py    # Engine and request-scoped sessions
      scanner.py      # Optional CCTV/webcam barcode worker
      schemas.py      # Validated API contracts
    tests/
  frontend/
    src/
      components/     # Shipment cards and status display
      lib/            # API client and device notifications
      types/          # Frontend API contracts
    capacitor.config.ts
  esp32/
    include/          # Board pins, configuration example, scan policy
    src/main.cpp      # Wi-Fi, camera capture, HTTPS submission, retry loop
    test/             # Host tests without hardware
    platformio.ini    # Pinned toolchain and camera board profiles
docs/
  architecture.md
  database.md
  integrations.md
  mobile.md
apps/backend/migrations/
  versions/           # Versioned Alembic migrations
apps/backend/alembic.ini
compose.yaml          # Local PostgreSQL with persistent storage
```

See [architecture and next steps](docs/architecture.md) and [tracking/CCTV integration](docs/integrations.md).

## Scope of this scaffold

This is a **development prototype**. The app and API bind to loopback by default. The backend now has basic member/admin JWT authentication for its shipment API, and the frontend integrates these endpoints. Backend records are not scoped to households. Household delivery events, protected CCTV capture, and Android remote push remain gaps. The optional ingestion key protects camera submissions; it is not a user identity. See the frontend handoff documents for the per-operation status.

No license has been chosen; add one before distributing the project.
