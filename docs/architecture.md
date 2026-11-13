# Architecture

The initial flow is synchronous and local. The camera worker is a separately launched process in the backend app, so continuous capture does not block FastAPI's lifecycle or start multiple times with API workers.

```mermaid
flowchart LR
  Camera[CCTV / webcam] --> Scanner[Optional Python barcode worker]
  Scanner -->|resi + courier + camera ID| API[FastAPI]
  UI[Vue / Capacitor] -->|Manual resi / refresh| API
  API --> Provider[TrackingProvider adapter]
  Provider --> Demo[Offline demo]
  Provider --> Gateway[Configurable HTTP gateway]
  API -->|psycopg pool| DB[(PostgreSQL)]
  Prisma[Prisma schema and migrations] --> DB
  DB --> Feed[In-app notification feed]
  Feed -->|Poll every 10 seconds| UI
  UI --> Alerts[Opt-in device notifications]
```

## Current behavior

1. Normalize resi numbers to uppercase and courier codes to lowercase; validate the payload.
2. Find an existing shipment using the unique `(courier, resi_number)` pair.
3. For a new shipment, call the provider, then persist its result and the initial notification in one transaction. Provider failures return HTTP 502 and do not create partial records.
4. Repeated camera detections update the last detection timestamp without repeating the lookup or notification. A database unique constraint also handles concurrent detections. Concurrent requests may still call the provider before the unique constraint resolves the race; use a distributed lock/idempotent queue before scaling workers.
5. Explicit refreshes store the current snapshot. A notification is created only when the normalized status changes. A failed refresh preserves the previous snapshot.
6. The dashboard polls the latest 100 shipments and notifications every 10 seconds. API list endpoints accept `limit` (1–500) and `offset`; dashboard totals describe its loaded page.

Couriers cannot reliably be inferred from the barcode alone. The scanner requires a configured courier; a future label classifier or courier selection screen can improve this. Only direct alphanumeric/hyphen resi barcodes are accepted. QR payloads containing URLs need a dedicated parser.

## Data and boundaries

`Shipment` stores the latest tracking snapshot, history supplied by the provider, source, camera ID, and timestamps. `Notification` stores durable in-app events. UUID identifiers keep clients independent of database sequence IDs.

PostgreSQL stores UUID identifiers, timezone-aware timestamps, enum status/source values, and JSONB tracking history. Prisma owns the schema and versioned migrations in `prisma/`. FastAPI uses psycopg for pooled PostgreSQL access; it does not run DDL at startup. This keeps the Python API while using Prisma's supported schema/migration tooling. See [database setup](database.md).

Registration inserts the shipment and its notification in a single transaction. `INSERT ... ON CONFLICT` resolves competing registrations with the unique courier/resi constraint. Refreshes acquire a PostgreSQL row lock so simultaneous requests that observe the same new status create a single status-change notification. Parameterized queries live in `repository.py`; connection pools open and close with the application lifespan. No footage is stored or sent to FastAPI by this scaffold.

Backend HTTP handlers are synchronous so blocking database/provider work runs in FastAPI's thread pool. The provider has a 10-second network timeout; the frontend has a 15-second request timeout. Tracking API secrets and ingestion keys stay in backend environment variables.

## Next implementation milestones

1. Choose a courier tracking API, map its responses into `TrackingSnapshot`, and confirm its terms, courier codes, quotas, and error responses.
2. Add users, per-user camera registration, shipment ownership, and authorization across every read/write endpoint. A shared ingestion key is not a user identity.
3. Move external tracking and notification delivery into a durable queue with retries, backoff, and an outbox. Keep the uniqueness invariant in the database.
4. Add scheduled refreshes for active shipments; handle terminal states, provider webhooks, and rate limits.
5. Add a real delivery channel (for example APNs/FCM or email) with per-user preferences, delivery attempts, deduplication, and device token rotation.
6. Improve camera reconnection, barcode crops, courier recognition, and field tests with actual label/camera combinations.

The camera source and credentials should stay on the household edge device. Treat resi numbers as private data; define retention and deletion rules when adding accounts.
