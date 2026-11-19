# Integrations

## Tracking providers

`TrackingProvider` in `apps/backend/src/cekrir/services/tracking.py` is the integration boundary. Its `lookup(resi_number, courier)` method returns a validated `TrackingSnapshot`.

The default `demo` adapter is an offline fixture. It returns `in_transit` for every valid input and is labeled in the dashboard. It cannot verify whether a real resi exists.

The `http` adapter makes a real request to a **normalized gateway that you operate**. This contract does not assume that a public courier API already supports this payload. Once you select a public API, either implement a provider class for it or translate that API in your gateway.

Set in `apps/backend/.env`:

```dotenv
CEKRIR_TRACKING_PROVIDER=http
CEKRIR_TRACKING_API_URL=https://your-gateway.example/track
CEKRIR_TRACKING_API_KEY=your-server-side-key
```

The adapter makes a POST to that exact URL:

```http
Authorization: Bearer <CEKRIR_TRACKING_API_KEY>
Content-Type: application/json

{"resi_number":"CEKRIR123456","courier":"jne"}
```

The authorization header is omitted if no key is configured. A successful response must be HTTP 2xx with this JSON shape:

```json
{
  "status": "in_transit",
  "summary": "Package arrived at the destination sorting hub",
  "history": [
    {
      "occurred_at": "2026-11-13T08:30:00Z",
      "description": "Arrived at sorting hub",
      "location": "Jakarta"
    }
  ]
}
```

Allowed statuses: `pending`, `in_transit`, `delivered`, `exception`. `history` defaults to an empty list and `location` is optional. Use timestamps with an explicit timezone. The provider rejects malformed responses and returns a sanitized HTTP 502 on timeouts, upstream errors, or invalid data. It does not follow redirects or retry automatically. Choose provider-specific handling for unknown resi numbers, quota exhaustion, and transient failures when writing the real adapter.

Never place API keys in `VITE_` variables; they become public frontend bundle contents.

## Optional CCTV / webcam worker

From `apps/backend`:

```sh
uv sync --extra vision --frozen
# Set CEKRIR_CAMERA_SOURCE in .env; defaults to local webcam index 0.
uv run --extra vision python -m cekrir.scanner --courier jne --camera-id front-door
```

The optional `vision` dependencies use OpenCV to read frames and ZXing to decode barcodes, including common Code 128 labels. The worker:

- Drains frames continuously and scans roughly once per second.
- Validates decoded values as direct resi numbers and posts them to `/api/v1/detections`.
- Suppresses successfully submitted duplicate codes for 60 seconds; the API adds persistent deduplication.
- Sends only resi/courier/camera identifiers, without uploading or recording video.
- Stops if a camera stream ends. Use a process supervisor to restart it; robust reconnect/backoff is a future improvement.

The courier must be configured explicitly; a barcode does not normally identify it. Several unrelated numeric codes can appear on a label. Validate camera placement, focus, label orientation, and expected barcode formats before treating this as unattended detection. There is no OCR fallback in the scaffold.

Set `CEKRIR_INGEST_API_KEY` in both the worker's environment and the backend's environment; the desktop worker requires it and sends the `X-Ingest-Key` header. If the worker is remote, set `CEKRIR_API_BASE_URL` to the API's reachable HTTPS base URL. Keep RTSP credentials in the ignored `.env`, not command history.

## ESP32 camera firmware

`apps/esp32` contains the camera capture client for the XIAO ESP32S3 Sense and AI Thinker ESP32-CAM. Its [README](../apps/esp32/README.md) covers hardware selection, configuration, build, flashing, and serial monitoring.

Firmware sends raw JPEG bytes to `POST /api/v1/detections/frame?courier=jne&camera_id=esp32-front-door`, with `Content-Type: image/jpeg` and the same required `X-Ingest-Key` used for JSON detections. The endpoint decodes common shipping barcodes with ZXing, ignores unsupported payloads such as QR URLs, and registers only a single unambiguous resi candidate. Its compact response includes `detected_count`, `ambiguous`, and `detections` containing the resi, shipment ID, and `created` flag.

JPEGs must fit within 512 KiB, 2 megapixels, and 2048 pixels per dimension. Request bodies are bounded even for chunked uploads; image dimensions are checked before decompression. The server does not write images to disk or the database. A blank frame returns HTTP 200 with zero detections. Multiple valid-looking resi numbers return HTTP 200 with `ambiguous: true` and no registration.

Unlike the desktop worker, this path uploads image frames to the API. Decoding is on the backend rather than on the ESP32. The courier remains explicitly configured; there is no OCR, courier classifier, or offline device-side decoding in the scaffold.

## Notifications

The backend keeps a persistent in-app notification feed at `GET /api/v1/notifications`. It records a new package and subsequent normalized status changes. Authenticated clients can also subscribe to `WS /api/v1/notifications/live`; the server publishes committed notification rows through Redis Pub/Sub. A short-lived JWT may be supplied in the WebSocket `Authorization: Bearer` header or as a `token` query parameter when the client cannot set headers.

Redis is configured with `CEKRIR_REDIS_URL` and starts with the local Compose stack. If Redis is unavailable, database writes still succeed and the persistent feed remains available, but live events are not delivered. The frontend currently polls its feed; it has not yet switched to the WebSocket endpoint.

The user can opt in to device notifications: the frontend uses browser Notifications on the web or Capacitor Local Notifications on native platforms. These alerts are generated from new events detected by foreground polling. Opening the dashboard does not replay historical events as device alerts. Browser permission requires localhost or a secure context and browser support.

Background push delivery is not implemented. A real production channel needs a backend dispatcher, user subscriptions, delivery retries and idempotency, and platform credentials. See [mobile setup](mobile.md).

## Authentication and roles

`POST /api/v1/auth/register` accepts `email`, `full_name`, and `password` and creates an unverified member. It sends an email and does not issue tokens. Configure `CEKRIR_SMTP_HOST`, `CEKRIR_SMTP_PORT`, `CEKRIR_SMTP_FROM`, and `CEKRIR_VERIFICATION_URL` in `apps/backend/.env`; set SMTP username/password if needed. `CEKRIR_SMTP_SECURITY` defaults to `starttls` and also supports `ssl` or `plain` (for a local mail sink). The verification URL can point to the API's `GET /api/v1/auth/verify-email` page. Use a publicly reachable HTTPS address for real users.

The recipient confirms the 30-minute, single-use link to verify the account. Clients can alternatively send its token to `POST /api/v1/auth/verify-email` as `{"token":"..."}`. `POST /api/v1/auth/resend-verification` accepts the original email and password; successful resends are limited to one per 60 seconds per account. If SMTP delivery fails after registration, the account remains pending and the user can request a resend. SMTP acceptance alone does not verify that the mailbox exists; only successful confirmation proves control of it. Existing accounts are grandfathered by the migration, and the configured bootstrap admin is trusted as verified.

After verification, `POST /api/v1/auth/login` accepts email and password and returns an access token valid for 15 minutes and a refresh token valid for 7 days. Send `{"refresh_token":"..."}` to `POST /api/v1/auth/refresh` to obtain a new pair. Only access tokens can authorize API and WebSocket requests; refresh tokens are accepted by the refresh endpoint. Tokens include email, full name, and role. Authorization and token renewal check the current account in the database. Refresh tokens remain valid until expiration and are not individually revocable. Password hashes use bcrypt with 12 rounds. Set a stable, random `CEKRIR_JWT_SECRET_KEY` of at least 32 characters in deployed environments; otherwise the backend generates a process-local key and tokens stop working after restart.

New registrations are members. Members can list shipments and notifications and add a shipment manually. Admins can list accounts with `GET /api/v1/auth/users`, refresh tracking, and change account roles with `PATCH /api/v1/auth/users/{user_id}/role`. Configure both `CEKRIR_BOOTSTRAP_ADMIN_EMAIL` and `CEKRIR_BOOTSTRAP_ADMIN_PASSWORD` to provision the first admin; later role changes require an admin token. When `CEKRIR_INGEST_API_KEY` is configured, JSON/JPEG camera ingestion requires the matching `X-Ingest-Key`; without it, ingestion requires an admin bearer token. This is a basic role boundary, not household ownership or per-family data isolation.

Run `pnpm run db:deploy` before starting the updated API. The full-name migration fills existing accounts with their email address as a placeholder. The optional `CEKRIR_BOOTSTRAP_ADMIN_FULL_NAME` sets the name of a newly provisioned bootstrap admin and defaults to `Administrator`.
