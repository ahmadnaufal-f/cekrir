# Backend API specification

This documents the implemented endpoints. The main API and the standalone camera server are separate processes with separate ports and authentication. The machine-readable OpenAPI files are [api/openapi.json](api/openapi.json) and [api/camera-openapi.json](api/camera-openapi.json); they describe request and response fields and validation rules. The main API also serves `/docs` and `/openapi.json` when running. WebSockets are described below because OpenAPI does not describe them.

From the repository root, regenerate the files after changing routes or models:

```powershell
& apps/backend/.venv/Scripts/python.exe apps/backend/scripts/export_api_specs.py
```

## Main API

The examples use `http://localhost:8000`. The main API requires its configured PostgreSQL database and migrations; Redis supports live notifications. JSON request and response bodies use `application/json`. Error responses generally contain `{"detail": "..."}`; validation errors use HTTP 422 with a list of error details.

Except for health and the public authentication endpoints, send `Authorization: Bearer <access_token>`. The access token lasts 15 minutes; the refresh token lasts seven days. Both contain the user ID, email, full name, role and token type. Permissions are checked against the user's current role in the database. Missing or invalid credentials return 401; insufficient permission returns 403.

| Method | Path | Permission / authentication | Request and result |
| --- | --- | --- | --- |
| GET | `/health` | Public | Returns `status`, configured `tracking_provider`, and Redis availability. |
| POST | `/api/v1/auth/register` | Public | JSON `email`, `full_name`, `password`; 201 with a verification message. Password: 12–72 characters and no more than 72 UTF-8 bytes. Duplicate email: 409; email service unavailable: 503. A 503 can occur after the account has been created. |
| POST | `/api/v1/auth/login` | Public | JSON `email`, `password`; returns access and refresh tokens, expiration times in seconds, and `user`. Invalid credentials or unverified email: 401. |
| POST | `/api/v1/auth/refresh` | Public | JSON `refresh_token`; returns a fresh token pair and user. Invalid or expired token: 401. |
| POST | `/api/v1/auth/verify-email` | Public | JSON `token` from the email; returns confirmation. Invalid or expired token: 400. |
| GET | `/api/v1/auth/verify-email?token=...` | Public | HTML verification page. The user confirms with its button, which posts the token. This page is excluded from the generated OpenAPI schema. |
| POST | `/api/v1/auth/resend-verification` | Public | JSON `email`, `password`; returns a generic verification message. Email service unavailable: 503. |
| GET | `/api/v1/auth/users` | `users:read` | Returns an array of users. |
| PATCH | `/api/v1/auth/users/{user_id}/role` | `users:role:update` | UUID `user_id`; JSON `role` is `admin` or `member`. Returns the updated user; 404 if missing, 409 for a conflicting location assignment. |
| GET | `/api/v1/shipments` | `shipments:read` | Returns shipments. Query `limit` defaults to 100, range 1–500; `offset` defaults to 0, minimum 0. |
| POST | `/api/v1/shipments` | `shipments:create` | JSON `resi_number`, `courier`. Returns shipment: 201 if created, 200 if already present. Tracking provider failure: 502. |
| POST | `/api/v1/shipments/{shipment_id}/refresh` | `shipments:refresh` | Refreshes tracking and returns the shipment; 404 if missing, 502 for provider failure. |
| POST | `/api/v1/detections` | `detections:create` or ingestion key as described below | JSON `resi_number`, `courier`, `camera_id`; returns `created` and `shipment`. |
| POST | `/api/v1/detections/frame?courier=jne&camera_id=door` | `detections:create` or ingestion key as described below | Raw JPEG body with `Content-Type: image/jpeg`; returns `detected_count`, `ambiguous`, and `detections`. |
| GET | `/api/v1/notifications` | `notifications:read` | Returns notifications. Supports the same `limit` and `offset` rules as shipments. |
| POST | `/api/v1/payments` | `payments:create` | JSON `reference`, integer `amount`, optional `currency` (`IDR`); `Idempotency-Key` header required. Returns a draft: 201 when created or 200 for an identical replay; 409 if the key is reused with different data. |
| GET | `/api/v1/payments/{payment_id}` | `payments:read` | Returns the authenticated user's payment draft by UUID; 404 if unavailable. |

For detection endpoints, if `CEKRIR_INGEST_API_KEY` is configured, the matching `X-Ingest-Key` header is required instead of bearer authentication. If it is not configured, a bearer token with `detections:create` is required. JPEG requests are limited to 512 KiB, 2 megapixels and 2048 pixels per side. Wrong content type returns 415, oversized body 413, and invalid image or metadata 422. The detector reports ambiguous multiple codes instead of creating a shipment. It does not save frames as images.

Payments are draft records only: no QRIS transaction or payment processing endpoint is implemented yet. Roles, permissions and locations exist in the data model, but there are currently no standalone CRUD endpoints for them.

### Live notifications WebSocket

Connect to `ws://localhost:8000/api/v1/notifications/live` with an access token in the `Authorization: Bearer <token>` header, or as the `token` query parameter for browser clients. The user needs `notifications:read`. The server first sends `{"type":"ready"}`, then sends notification JSON objects when Redis publishes them. Authentication failures close with code 4401; Redis failures close with code 1013. A query-string token may appear in logs, so prefer the header when the client supports it.

## Standalone camera server

Run `apps/backend/run_camera.bat` on Windows or `apps/backend/.venv/Scripts/python.exe apps/backend/run_camera.py` from the repository root. The server listens on port 8001 and reads its camera username and password from the local, Git-ignored `apps/esp32/include/wifi_camera_config.h`. All routes require HTTP Basic authentication. The browser prompts for the same credentials. This is a separate application from the main API and does not require PostgreSQL or Redis.

| Method | Path | Request and result |
| --- | --- | --- |
| POST | `/camera/frame` | Raw `image/jpeg` body; returns `{"status":"received"}`. Invalid JPEG: 422, wrong content type: 415, body over 512 KiB: 413. The JPEG dimension limits match those above. |
| GET | `/camera/latest.jpg` | Most recently received JPEG; 404 until the first frame. |
| GET | `/camera` | HTML page that refreshes the latest picture once per second. |
| GET | `/camera/video` | HTML page showing the MJPEG stream. |
| GET | `/camera/stream` | Continuous `multipart/x-mixed-replace; boundary=frame` response containing new JPEG frames. |

Only the latest frame is held in process memory; it is cleared when the server stops. When uploads stop, the displayed frame may remain visible. The ESP32 picture firmware sends approximately one frame per second; the video firmware targets up to approximately ten, subject to capture and network speed. The stream has no audio and does not record video. Credentials and frames travel over unencrypted HTTP, so use these endpoints only on a trusted local network and do not expose them to the internet.
