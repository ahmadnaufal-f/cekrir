# Cekrir

GitHub-connected frontend deployment: https://cekrir-frontend.vercel.app (current release also at https://cekrir.vercel.app). Production UI has live integrations unavailable and development mocks disabled. Vercel authentication may be required. The frontend work is on `frontend/household-vercel`; `main` is unchanged. See the [deployment record](docs/frontend/vercel-deployment.md).

A monorepo for a household delivery app. The confirmed target uses proximity-triggered **ESP32 camera images** for Python barcode decoding; the selected **BARDI CCTV** supplies the separate delivery photo. The existing backend and firmware remain scaffold implementations pending alignment.

The frontend now implements household screens with explicit development mocks. Auth, delivery events, photos, devices, members, and Android server push are **not live integrations**. See the [frontend specification map](docs/frontend/spec-map.md), [integration and verification report](docs/frontend/integration-status.md), and [backend/firmware handoff](docs/frontend/backend-gaps.md).

Three apps, one repository:

| App             | Stack                                      | Purpose                                                             |
| --------------- | ------------------------------------------ | ------------------------------------------------------------------- |
| `apps/backend`  | Python 3.12+, FastAPI, psycopg, PostgreSQL | Detection ingestion, tracking, persistence, notification feed       |
| `apps/frontend` | Vue 3, TypeScript, Vite, Capacitor         | Household delivery UI; Android acceptance target, iOS unverified    |
| `apps/esp32`    | Arduino C++, PlatformIO                    | Camera firmware that sends JPEG frames to the barcode detection API |

The default tracking provider is an explicitly labeled **offline demo**. It never calls a courier API. The HTTP provider and camera worker can be enabled separately. Integrations stay configurable until a real tracking API and notification channel are selected.

## Documentation

- [Product requirements (PRD)](docs/prd.md): scope, decisions, research, and open questions.
- [Backend deployment discussion](docs/backend-deployment.md): laptop, tunnel, and cloud options for team review.

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

The frontend defaults to live mode and reports unsupported household operations. To review the frontend without a backend, run `VITE_APP_MODE=mock pnpm run dev:frontend`. Sign in with `admin@demo.test` or `anggota`, password `demo1234`. These are synthetic development accounts; sessions and new fixture records are in memory only. Production builds ignore mock mode and exclude the fixture module. The manual shipment client remains as legacy scaffold code, separate from household events.

Backend demo tracking always reports `in_transit`; it is sample data. PostgreSQL persists in the Compose `postgres_data` volume. The root dev command starts both apps and stops them together with Ctrl+C; `pnpm run db:down` stops PostgreSQL while preserving its volume.

**Prisma owns the database schema and versioned SQL migrations.** FastAPI uses psycopg and a connection pool because Prisma's supported client targets JavaScript/TypeScript. The schema is defined once in `prisma/schema.prisma`; the Python backend does not create or migrate tables. See [database setup](docs/database.md) for schema changes, testing, and deployment.

## Try a camera detection without a camera

With the API running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/detections \
  -H 'Content-Type: application/json' \
  -d '{"resi_number":"CEKRIR987654","courier":"jne","camera_id":"front-door"}'
```

This legacy backend detection creates a shipment and feed notification; it does not populate the household mock UI or deliver remote push. Its permanent courier/resi uniqueness differs from the target household delivery-event deduplication window. If `CEKRIR_INGEST_API_KEY` is configured, also send the matching `X-Ingest-Key` header.

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

| Command                                                     | Purpose                                                   |
| ----------------------------------------------------------- | --------------------------------------------------------- |
| `pnpm run dev`                                              | Run FastAPI and Vite                                      |
| `pnpm run dev:backend`                                      | Run FastAPI only                                          |
| `pnpm run dev:frontend`                                     | Run Vite only                                             |
| `pnpm run check`                                            | Oxfmt, Oxlint, Prisma, Python lint, Vue/TypeScript checks |
| `pnpm test`                                                 | API integration tests and frontend API tests              |
| `pnpm run build`                                            | Type check and build the frontend                         |
| `pnpm run format`                                           | Format Python and web/docs/config files                   |
| `pnpm run db:up`                                            | Start local PostgreSQL and wait for readiness             |
| `pnpm run db:down`                                          | Stop local PostgreSQL; keep persisted data                |
| `pnpm run db:deploy`                                        | Apply committed Prisma migrations                         |
| `pnpm run db:migrate --name change_name`                    | Create and apply a development migration                  |
| `pnpm run db:studio`                                        | Inspect PostgreSQL data with Prisma Studio                |
| `pnpm run firmware:build`                                   | Cross-compile the default ESP32S3 camera profile          |
| `pnpm run firmware:build --environment ai_thinker_esp32cam` | Cross-compile the AI Thinker profile                      |
| `pnpm run firmware:test`                                    | Run firmware policy tests on the host                     |
| `pnpm run firmware:upload --environment xiao_esp32s3_sense` | Flash a connected device                                  |
| `pnpm run firmware:monitor`                                 | Open the serial monitor at 115200 baud                    |

`pnpm test` applies Prisma migrations to `TEST_DATABASE_URL` and runs the API tests against that dedicated PostgreSQL database. Compose creates `cekrir_test` on its first initialization. Tests clear its shipment/notification tables; they require a database name ending in `_test` and reject the application database. Frontend tests do not need PostgreSQL.

Python dependencies live in `apps/backend/pyproject.toml` and `apps/backend/uv.lock`. The frontend is a pnpm workspace defined in `pnpm-workspace.yaml`, with a root `pnpm-lock.yaml`. Commit both lockfiles when dependencies change. CI runs the same checks with frozen dependency installation.

Formatting uses Oxfmt and JavaScript/TypeScript linting uses Oxlint with Vue and Vitest support. See [tooling setup](docs/tooling.md) for versions, editor integration, focused frontend checks, and formatting commands.

## Mobile apps

Capacitor uses `apps/frontend/dist` as its web bundle. See [mobile setup](docs/mobile.md) for Android/iOS configuration, HTTPS API access, and notification limitations.

## Project map

```text
apps/
  backend/
    src/cekrir/
      api/            # HTTP routes and dependencies
      services/       # Tracking adapters and shipment workflow
      scanner.py      # Optional CCTV/webcam barcode worker
      repository.py   # PostgreSQL queries and atomic writes
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
prisma/
  schema.prisma       # Canonical PostgreSQL schema
  migrations/         # Versioned SQL migrations
prisma.config.ts      # Shared DATABASE_URL and Prisma tooling
compose.yaml          # Local PostgreSQL with persistent storage
```

See [architecture and next steps](docs/architecture.md) and [tracking/CCTV integration](docs/integrations.md).

## Scope of this scaffold

This is a **development prototype**. The app and API bind to loopback by default. Household account and role flows exist only as frontend fixtures. Backend authorization, delivery-event persistence, protected CCTV capture, and Android remote push remain gaps. The optional ingestion key only protects camera submissions; it is not user authorization. See the frontend handoff documents for the per-operation status.

No license has been chosen; add one before distributing the project.
