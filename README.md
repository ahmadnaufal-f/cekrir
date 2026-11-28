# Cekrir

GitHub-connected frontend deployment: https://cekrir-frontend.vercel.app (current release also at https://cekrir.vercel.app). Production UI has live integrations unavailable and development mocks disabled. Vercel authentication may be required. The frontend work is on `frontend/household-vercel`; `main` is unchanged. See the [deployment record](docs/frontend/vercel-deployment.md).

A monorepo for a household delivery app. The confirmed target uses proximity-triggered **ESP32 camera images** for Python barcode decoding; the selected **BARDI CCTV** supplies the separate delivery photo. The existing backend and firmware remain scaffold implementations pending alignment.

The frontend has household screens and development mocks. The backend now supports Tuya delivery photos, but the frontend has no photo viewer yet. Live integration coverage varies by screen; see the [frontend specification map](docs/frontend/spec-map.md), [integration report](docs/frontend/integration-status.md), and [backend handoff](docs/frontend/backend-gaps.md).

Three apps, one repository:

| App             | Stack                                                         | Purpose                                                                |
| --------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `apps/backend`  | Python 3.12+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis | Authenticated detection, tracking, persistence, live notification feed |
| `apps/frontend` | Vue 3, TypeScript, Vite, Capacitor                            | Household delivery UI; Android acceptance target, iOS unverified       |
| `apps/esp32`    | Arduino C++, PlatformIO                                       | Camera firmware that sends JPEG frames to the barcode detection API    |

The default tracking provider is an explicitly labeled **offline demo**. It never calls a courier API. The HTTP provider and camera worker can be enabled separately. Shipment and notification routes use JWT authentication; camera submissions can use the optional ingestion key. Live notification events use Redis Pub/Sub, while PostgreSQL remains the durable notification store.

## Documentation

- [Product requirements (PRD)](docs/prd.md): scope, decisions, research, and open questions.
- [Backend deployment discussion](docs/backend-deployment.md): laptop, tunnel, and cloud options for team review.
- [Ubuntu VM setup](docs/ubuntu-vm-setup.md): Docker, PostgreSQL, Redis, Nginx, and HTTPS for the backend.
- [Payment preparation](docs/payments.md): idempotent drafts and QRIS integration requirements.
- [Roles, permissions, and locations](docs/roles-locations.md): access checks and location ownership.

These pages were imported from Notion so they can be read and discussed on GitHub. Their planning statuses are preserved; implementation details are documented below and in the existing engineering docs.

## Start locally

Install **Node.js 24 LTS**, pnpm 11, [uv](https://docs.astral.sh/uv/getting-started/installation/), and configure PostgreSQL and Redis accessible to the backend. uv can install the required Python version. For the VM Docker deployment, follow the [Ubuntu VM setup](docs/ubuntu-vm-setup.md).

```sh
git clone https://github.com/ahmadnaufal-f/cekrir.git
cd cekrir
corepack enable
pnpm install --frozen-lockfile
uv sync --project apps/backend --frozen
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env
pnpm run db:deploy
pnpm run dev
```

- Dashboard: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

To enable admin-only tracking refresh and role management, set both `CEKRIR_BOOTSTRAP_ADMIN_EMAIL` and `CEKRIR_BOOTSTRAP_ADMIN_PASSWORD` in `apps/backend/.env` before the first API start. Configure SMTP for `POST /api/v1/auth/register`; new members confirm their email before signing in. See [authentication and role setup](docs/integrations.md#authentication-and-roles).

The frontend defaults to live mode and reports unsupported household operations. To review the frontend without a backend, run `VITE_APP_MODE=mock pnpm run dev:frontend`. Sign in with `admin@demo.test` or `anggota`, password `demo1234`. These are synthetic development accounts; sessions and new fixture records are in memory only. Production builds ignore mock mode and exclude the fixture module. The manual shipment client remains as legacy scaffold code, separate from household events.

Backend demo tracking always reports `in_transit`; it is sample data. The root dev command starts both apps and stops them together with Ctrl+C. The VM Compose setup stores PostgreSQL in its `vm_postgres_data` volume.

**SQLAlchemy owns the backend ORM models and Alembic owns versioned migrations.** The model package is in `apps/backend/src/cekrir/db/model`; run committed migrations with `pnpm run db:deploy`. Existing Prisma migration files are retained as a historical record and are no longer used. See [database setup](docs/database.md) for schema changes, testing, and deployment.

## Try a camera detection without a camera

With the API running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/detections \
  -H 'Content-Type: application/json' \
  -d '{"resi_number":"CEKRIR987654","courier":"jne","camera_id":"front-door"}'
```

This backend detection creates a shipment and feed notification. If `CEKRIR_INGEST_API_KEY` is configured, send the matching `X-Ingest-Key` header; otherwise use an admin bearer token. With Tuya configured, the first accepted detection also queues one CCTV photo. Its permanent courier/resi uniqueness differs from the target household delivery-event deduplication window.

## Tuya delivery photos

Set `TUYA_API_KEY`, `TUYA_API_ENDPOINT`, and `TUYA_CCTV_DEVICE_ID` in the ignored `apps/backend/.env`. The device ID must identify the selected delivery camera in the Tuya account. The backend requires all three values together and uses HTTPS to request one JPEG after either `POST /api/v1/detections` or a successfully decoded `POST /api/v1/detections/frame`. Run `pnpm run db:deploy` after updating the backend. See [the cloud capture test](docs/tuya-cloud-capture-research.md).

The scan response is independent of capture: it reports `photo_status: "pending"` when a photo is queued. Read `GET /api/v1/shipments/{id}` for the current status. Once `ready`, its `photo_url` points to `GET /api/v1/shipments/{id}/photo`, which requires a bearer token with `shipments:read`. Clients must fetch the JPEG with that token; an ordinary unauthenticated image tag cannot load it. Capture failures set `photo_status: "unavailable"` while preserving the shipment and notification. Duplicate scans of the same courier and resi do not queue another photo.

JPEGs are saved under `CEKRIR_CCTV_PHOTO_DIR` (default `data/cctv-photos/`, ignored by Git). Mount that directory on persistent storage for a deployed backend. The current capture task runs inside the API process; a process crash can leave a photo marked `pending`, so a durable worker is needed before relying on this flow for high availability.

The [Tuya QR account-linking POC](docs/tuya-qr-link-poc.md) tests Cloud Project access to a camera paired to a separate Tuya account.

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

| Command                                                     | Purpose                                                                          |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `pnpm run dev`                                              | Run FastAPI and Vite                                                             |
| `pnpm run dev:backend`                                      | Run FastAPI only                                                                 |
| `pnpm run dev:frontend`                                     | Run Vite only                                                                    |
| `pnpm run check`                                            | Oxfmt, Oxlint, Alembic schema check, Python lint, Vue/TypeScript checks          |
| `pnpm test`                                                 | API integration tests and frontend API tests                                     |
| `pnpm run build`                                            | Type check and build the frontend                                                |
| `pnpm run format`                                           | Format Python and web/docs/config files                                          |
| `pnpm run db:up`                                            | Start the VM Compose PostgreSQL and Redis services; requires `apps/backend/.env` |
| `pnpm run db:down`                                          | Stop the VM Compose services; keep persisted data                                |
| `pnpm run db:deploy`                                        | Apply committed Alembic migrations                                               |
| `pnpm run db:migrate -- -m "change_name"`                   | Generate an Alembic migration for review                                         |
| `pnpm run firmware:build`                                   | Cross-compile the default ESP32S3 camera profile                                 |
| `pnpm run firmware:build --environment ai_thinker_esp32cam` | Cross-compile the AI Thinker profile                                             |
| `pnpm run firmware:test`                                    | Run firmware policy tests on the host                                            |
| `pnpm run firmware:upload --environment xiao_esp32s3_sense` | Flash a connected device                                                         |
| `pnpm run firmware:monitor`                                 | Open the serial monitor at 115200 baud                                           |

`pnpm test` applies Alembic migrations to `TEST_DATABASE_URL` and runs the API tests against that dedicated PostgreSQL database. Create the test database separately; the VM Compose setup does not create or expose one. Tests clear its shipment/notification tables; they require a database name ending in `_test` and reject the application database. Frontend tests do not need PostgreSQL.

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
apps/backend/compose.yaml  # VM backend, PostgreSQL, and Redis
```

See [architecture and next steps](docs/architecture.md) and [tracking/CCTV integration](docs/integrations.md).

## Scope of this scaffold

This is a **development prototype**. The app and API bind to loopback by default. Backend records are not scoped to households. Household delivery events and Android remote push remain gaps. The backend has protected Tuya CCTV photos, while the frontend does not yet display them. The optional ingestion key protects camera submissions; it is not a user identity. See the frontend handoff documents for the per-operation status.

This project is licensed under the [MIT License](LICENSE).
