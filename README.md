# Cekrir

A starter monorepo for a package checking service: decode a **resi** (shipment tracking number) from a CCTV barcode, look it up through a tracking provider, and collect package notifications.

Two apps, one repository:

| App             | Stack                                   | Purpose                                                       |
| --------------- | --------------------------------------- | ------------------------------------------------------------- |
| `apps/backend`  | Python 3.12+, FastAPI, SQLModel, SQLite | Detection ingestion, tracking, persistence, notification feed |
| `apps/frontend` | Vue 3, TypeScript, Vite, Capacitor      | Web dashboard and Android/iOS app shell                       |

The default tracking provider is an explicitly labeled **offline demo**. It never calls a courier API. The HTTP provider and camera worker can be enabled separately. Integrations stay configurable until a real tracking API and notification channel are selected.

## Start locally

Install **Node.js 24 LTS**, npm 11+, and [uv](https://docs.astral.sh/uv/getting-started/installation/). uv can install the required Python version.

```sh
git clone https://github.com/ahmadnaufal-f/cekrir.git
cd cekrir
npm ci
uv sync --project apps/backend --frozen
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env
npm run dev
```

- Dashboard: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

Add `CEKRIR123456` with courier `jne` in the dashboard to exercise the flow. Demo tracking always reports `in_transit`; it is sample data. SQLite persists at `apps/backend/data/cekrir.db`. The root dev command starts both apps and stops them together with Ctrl+C.

## Try a camera detection without a camera

With the API running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/detections \
  -H 'Content-Type: application/json' \
  -d '{"resi_number":"CEKRIR987654","courier":"jne","camera_id":"front-door"}'
```

The dashboard polls every 10 seconds. The detection creates a shipment and a notification. Repeat the request: the same courier/resi pair keeps a single shipment and does not send another tracking request or create another notification. If `CEKRIR_INGEST_API_KEY` is configured, also send the matching `X-Ingest-Key` header.

## Commands

Run these from the repository root:

| Command                | Purpose                                          |
| ---------------------- | ------------------------------------------------ |
| `npm run dev`          | Run FastAPI and Vite                             |
| `npm run dev:backend`  | Run FastAPI only                                 |
| `npm run dev:frontend` | Run Vite only                                    |
| `npm run check`        | Formatting, Python lint, Vue/TypeScript checking |
| `npm test`             | API integration tests and frontend API tests     |
| `npm run build`        | Type check and build the frontend                |
| `npm run format`       | Format Python and web/docs/config files          |

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
      models.py       # Persisted shipments and notification events
      schemas.py      # Validated API contracts
    tests/
  frontend/
    src/
      components/     # Shipment cards and status display
      lib/            # API client and device notifications
      types/          # Frontend API contracts
    capacitor.config.ts
docs/
  architecture.md
  integrations.md
  mobile.md
```

See [architecture and next steps](docs/architecture.md) and [tracking/CCTV integration](docs/integrations.md).

## Scope of this scaffold

This is a **single workspace development prototype**. The dashboard and API bind to loopback by default. User accounts, tenant ownership, production authorization, automatic scheduled tracking refreshes, durable background delivery, and background mobile push are future work. The optional ingestion key only protects camera submissions. Do not expose this shared workspace API to the public internet before adding user authentication and ownership checks.

No license has been chosen; add one before distributing the project.
