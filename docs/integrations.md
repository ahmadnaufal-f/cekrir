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

Set `CEKRIR_INGEST_API_KEY` in both the worker's environment and the backend's environment to require the `X-Ingest-Key` header on camera submissions. If the worker is remote, set `CEKRIR_API_BASE_URL` to the API's reachable HTTPS base URL. Keep RTSP credentials in the ignored `.env`, not command history.

## Notifications

The working default is a persistent in-app notification feed at `GET /api/v1/notifications`. It records a new package and subsequent normalized status changes. This lets the complete local flow work without sending external messages.

The user can opt in to device notifications: the frontend uses browser Notifications on the web or Capacitor Local Notifications on native platforms. These alerts are generated from new events detected by **foreground polling**. Opening the dashboard does not replay historical events as device alerts. Browser permission requires localhost or a secure context and browser support.

Background push delivery is not implemented. A real production channel needs a backend dispatcher, user subscriptions, delivery retries and idempotency, and platform credentials. See [mobile setup](mobile.md).
