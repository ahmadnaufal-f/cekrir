# Cekrir

A starter monorepo for a package checking service: decode a **resi** (shipment tracking number) from a CCTV barcode, look it up through a tracking provider, and collect package notifications.

Three apps, one repository:

| App             | Stack                                      | Purpose                                                             |
| --------------- | ------------------------------------------ | ------------------------------------------------------------------- |
| `apps/backend`  | Python 3.12+, FastAPI, psycopg, PostgreSQL | Detection ingestion, tracking, persistence, notification feed       |
| `apps/frontend` | Vue 3, TypeScript, Vite, Capacitor         | Web dashboard and Android/iOS app shell                             |
| `apps/esp32`    | Arduino C++, PlatformIO                    | Camera firmware that sends JPEG frames to the barcode detection API |

The default tracking provider is an explicitly labeled **offline demo**. It never calls a courier API. The HTTP provider and camera worker can be enabled separately. Integrations stay configurable until a real tracking API and notification channel are selected.

## Start locally

Install **Node.js 24 LTS**, npm 11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and **Docker with Compose**. uv can install the required Python version. An existing PostgreSQL server can also be used instead of Docker.

```sh
git clone https://github.com/ahmadnaufal-f/cekrir.git
cd cekrir
npm ci
uv sync --project apps/backend --frozen
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env
npm run db:up
npm run db:deploy
npm run dev
```

- Dashboard: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

Add `CEKRIR123456` with courier `jne` in the dashboard to exercise the flow. Demo tracking always reports `in_transit`; it is sample data. PostgreSQL persists in the Compose `postgres_data` volume. The root dev command starts both apps and stops them together with Ctrl+C; `npm run db:down` stops PostgreSQL while preserving its volume.

**Prisma owns the database schema and versioned SQL migrations.** FastAPI uses psycopg and a connection pool because Prisma's supported client targets JavaScript/TypeScript. The schema is defined once in `prisma/schema.prisma`; the Python backend does not create or migrate tables. See [database setup](docs/database.md) for schema changes, testing, and deployment.

## Try a camera detection without a camera

With the API running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/detections \
  -H 'Content-Type: application/json' \
  -d '{"resi_number":"CEKRIR987654","courier":"jne","camera_id":"front-door"}'
```

The dashboard polls every 10 seconds. The detection creates a shipment and a notification. Repeat the request: the same courier/resi pair keeps a single shipment and does not send another tracking request or create another notification. If `CEKRIR_INGEST_API_KEY` is configured, also send the matching `X-Ingest-Key` header.

## ESP32 camera scanner

The [ESP32 app](apps/esp32/README.md) includes PlatformIO profiles for **Seeed XIAO ESP32S3 Sense** and **AI Thinker ESP32-CAM**. Start with a camera-equipped board with PSRAM and evaluate its optics with actual shipping labels before buying a batch.

The firmware uploads small JPEG snapshots to `POST /api/v1/detections/frame`. FastAPI decodes Code 128, Code 39, ITF, or direct-resi QR barcodes and reuses shipment tracking and notification deduplication. Decoding runs on the server; frames are processed in memory without being stored. Multiple possible resi codes in one frame are reported as ambiguous and create no shipments.

```sh
cp apps/esp32/include/config.example.h apps/esp32/include/config.h
# Set Wi-Fi, API URL, camera ID, courier, ingestion key, and HTTPS root CA.
npm run firmware:build
npm run firmware:test
```

See the firmware README for flashing, a trusted LAN development setup, board selection, frame limits, and hardware validation steps.

## Commands

Run these from the repository root:

| Command                                                       | Purpose                                          |
| ------------------------------------------------------------- | ------------------------------------------------ |
| `npm run dev`                                                 | Run FastAPI and Vite                             |
| `npm run dev:backend`                                         | Run FastAPI only                                 |
| `npm run dev:frontend`                                        | Run Vite only                                    |
| `npm run check`                                               | Formatting, Python lint, Vue/TypeScript checking |
| `npm test`                                                    | API integration tests and frontend API tests     |
| `npm run build`                                               | Type check and build the frontend                |
| `npm run format`                                              | Format Python and web/docs/config files          |
| `npm run db:up`                                               | Start local PostgreSQL and wait for readiness    |
| `npm run db:down`                                             | Stop local PostgreSQL; keep persisted data       |
| `npm run db:deploy`                                           | Apply committed Prisma migrations                |
| `npm run db:migrate -- --name change_name`                    | Create and apply a development migration         |
| `npm run db:studio`                                           | Inspect PostgreSQL data with Prisma Studio       |
| `npm run firmware:build`                                      | Cross-compile the default ESP32S3 camera profile |
| `npm run firmware:build -- --environment ai_thinker_esp32cam` | Cross-compile the AI Thinker profile             |
| `npm run firmware:test`                                       | Run firmware policy tests on the host            |
| `npm run firmware:upload -- --environment xiao_esp32s3_sense` | Flash a connected device                         |
| `npm run firmware:monitor`                                    | Open the serial monitor at 115200 baud           |

`npm test` applies Prisma migrations to `TEST_DATABASE_URL` and runs the API tests against that dedicated PostgreSQL database. Compose creates `cekrir_test` on its first initialization. Tests clear its shipment/notification tables; they require a database name ending in `_test` and reject the application database. Frontend tests do not need PostgreSQL.

Python dependencies live in `apps/backend/pyproject.toml` and `apps/backend/uv.lock`. The frontend is an npm workspace with a root `package-lock.json`. Commit both lockfiles when dependencies change. CI runs the same checks with frozen dependency installation.

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

This is a **single workspace development prototype**. The dashboard and API bind to loopback by default. User accounts, tenant ownership, production authorization, automatic scheduled tracking refreshes, durable background delivery, and background mobile push are future work. The optional ingestion key only protects camera submissions. Do not expose this shared workspace API to the public internet before adding user authentication and ownership checks.

No license has been chosen; add one before distributing the project.
