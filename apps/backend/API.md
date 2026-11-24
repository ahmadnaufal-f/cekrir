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
| POST | `/api/v1/auth/register` | Public | JSON `email`, `full_name`, `password`; 201 with a verification message and `location_id` and `esp_device_id` set to null. New accounts are inactive members without a location until assigned by an admin. Password: 12–72 characters and no more than 72 UTF-8 bytes. Duplicate email: 409; email service unavailable: 503. A 503 can occur after the inactive account has been created; use the resend-verification endpoint to retry. |
| POST | `/api/v1/auth/login` | Public | JSON `email`, `password`; returns tokens, `user`, `location_id` and `esp_device_id`. Admin login creates a default location and ESP identifier if needed and reuses them on later logins. Invalid credentials or unverified email: 401. |
| POST | `/api/v1/auth/refresh` | Public | JSON `refresh_token`; returns a fresh token pair, user, `location_id` and `esp_device_id`. Invalid or expired token: 401. |
| POST | `/api/v1/auth/verify-email` | Public | JSON `token` from the email; confirms the address and activates the account. Invalid or expired token: 400. |
| GET | `/api/v1/auth/verify-email?token=...` | Public | HTML verification page. The user confirms with its button, which posts the token. This page is excluded from the generated OpenAPI schema. |
| POST | `/api/v1/auth/resend-verification` | Public | JSON `email`, `password`; works for inactive unverified users and returns a generic verification message. A new link is sent at most once per 60 seconds. Email service unavailable: 503. |
| GET | `/api/v1/auth/users` | `users:read` | Returns an array of users. |
| PATCH | `/api/v1/auth/users/{user_id}/role` | `users:role:update` | UUID `user_id`; JSON `role` is `admin` or `member`. Returns the updated user; 404 if missing, 409 for a conflicting location assignment. |
| GET | `/api/v1/shipments` | `shipments:read` | Returns shipments. Query `limit` defaults to 100, range 1–500; `offset` defaults to 0, minimum 0. |
| POST | `/api/v1/shipments` | `shipments:create` | JSON `resi_number`, `courier`. Returns shipment: 201 if created, 200 if already present. Tracking provider failure: 502. |
| POST | `/api/v1/shipments/analyze-screenshot` | `shipments:create` | Raw PNG, JPEG, or WebP. Returns extracted shipment fields for review. See [Screenshot autofill](#screenshot-autofill). |
| POST | `/api/v1/shipments/{shipment_id}/refresh` | `shipments:refresh` | Refreshes tracking and returns the shipment; 404 if missing, 502 for provider failure. |
| POST | `/api/v1/tracking/binderbyte` | `shipments:read` | JSON `resi_number`, `courier`, optional `phone_last_five`; returns BinderByte summary, detail and history; 503 when unavailable or unconfigured. |
| POST | `/api/v1/devices/{device_id}/frames?courier=jne` | `X-Device-Key` | Raw JPEG from the assigned ESP. Authenticates its individual key, records its check-in and processes barcodes. |
| POST | `/api/v1/detections` | `detections:create` or ingestion key as described below | JSON `resi_number`, `courier`, `camera_id`; returns `created` and `shipment`. |
| POST | `/api/v1/detections/frame?courier=jne&camera_id=door` | `detections:create` or ingestion key as described below | Raw JPEG body with `Content-Type: image/jpeg`; returns `detected_count`, `ambiguous`, and `detections`. |
| GET | `/api/v1/notifications` | `notifications:read` | Returns notifications. Supports the same `limit` and `offset` rules as shipments. |
| POST | `/api/v1/notifications/fcm` | `notifications:read` | JSON `token`, `location_id`; associates a push token with the authenticated user and an accessible location. |
| POST | `/api/v1/notifications/fcm/unregister` | `notifications:read` | JSON `token`; removes the authenticated user's push registration. |
| DELETE | `/api/v1/notifications/fcm/{device_id}` | `notifications:read` | Removes the authenticated user's push registration by its returned UUID. |
| POST | `/api/v1/notifications/email` | `notifications:send` | JSON `user_id`, `subject`, `message`; requires `Idempotency-Key`. Sends to the authenticated admin or an active, verified member of a location the admin owns. Returns 404 for an unavailable recipient and 503 for delivery errors. |
| GET | `/api/v1/locations` | `locations:manage` | Lists owned locations, each with `esp_device_id`, `onboarding_complete`, and `camera_ids`. |
| POST | `/api/v1/locations` | `locations:manage` | JSON `name`; creates a location owned by the admin. Onboarding is incomplete until an ESP is assigned. |
| POST | `/api/v1/locations/{location_id}/esp/credentials` | `locations:manage` | Rotates the ESP key and returns `device_id` and `device_key` once. Previously issued keys stop working. |
| POST | `/api/v1/locations/{location_id}/cctv` | `locations:manage` | JSON `name`, `stream_url`, `username`, `password`; encrypts the connection details and returns the camera ID and name. |
| GET | `/api/v1/locations/{location_id}/cctv` | `locations:manage` | Lists the location's CCTV cameras without returning their connection details. |
| PUT | `/api/v1/locations/{location_id}/esp/{device_id}` | `locations:manage` | Assigns an ESP identifier to an owned location. Idempotent for the same assignment; returns 409 if either the location or ESP is already assigned elsewhere. |
| DELETE | `/api/v1/locations/{location_id}/esp` | `locations:manage` | Removes the ESP assignment, making onboarding incomplete until another ESP is assigned. |
| PUT | `/api/v1/locations/{location_id}/members/{user_id}` | `locations:manage` | Assigns a user to an admin-owned location; repeats are safe. |
| PUT | `/api/v1/locations/{location_id}/cameras/{camera_id}` | `locations:manage` | Assigns a camera ID to an admin-owned location; repeats are safe. Returns 409 if assigned elsewhere. |
| DELETE | `/api/v1/locations/{location_id}/members/{user_id}` | `locations:manage` | Removes a member from an admin-owned location; repeats are safe. |
| DELETE | `/api/v1/locations/{location_id}/cameras/{camera_id}` | `locations:manage` | Removes a camera assignment from an admin-owned location; repeats are safe. |
| POST | `/api/v1/payments` | `payments:create` | JSON `reference`, integer `amount`, optional `currency` (`IDR`); `Idempotency-Key` header required. Returns a draft: 201 when created or 200 for an identical replay; 409 if the key is reused with different data. |
| GET | `/api/v1/payments/{payment_id}` | `payments:read` | Returns the authenticated user's payment draft by UUID; 404 if unavailable. |

For detection endpoints, if `CEKRIR_INGEST_API_KEY` is configured, the matching `X-Ingest-Key` header is required instead of bearer authentication. If it is not configured, a bearer token with `detections:create` is required. JPEG requests are limited to 512 KiB, 2 megapixels and 2048 pixels per side. Wrong content type returns 415, oversized body 413, and invalid image or metadata 422. The detector reports ambiguous multiple codes instead of creating a shipment. It does not save frames as images.

Payments are draft records only: no QRIS transaction or payment processing endpoint is implemented yet. Roles and permissions have no standalone CRUD endpoints. A location can have at most one ESP and any number of cameras. `onboarding_complete` becomes true after the assigned ESP makes an authenticated frame request. A matching physical detection sets the existing shipment to delivered without replacing its other details; a new barcode creates a delivered shipment. The configured CCTV details are stored for later use; registering a CCTV does not start a camera connection or scanning worker.

Login and refresh report the oldest accessible location and its ESP ID, if any. Admins can list all their locations with `GET /api/v1/locations`. An unassigned member, or a location without an assigned ESP, receives null for the missing ID. An ESP ID alone does not grant access; only the location admin can issue its device key.

See [device, push, and tracking setup](../../docs/device-onboarding.md) for the frontend and ESP flow, required secrets, Firebase setup, and BinderByte configuration.

### Email notifications

In-app and email are separate delivery channels: `GET /api/v1/notifications` and the WebSocket serve the frontend, while `POST /api/v1/notifications/email` sends an individual email. A package event can be delivered to both channels; a Redis failure does not prevent an email attempt, and an email delivery failure does not prevent Redis publication. The database notification is saved before delivery. These are best-effort live deliveries, not a background retry queue.

Select Resend by setting `CEKRIR_EMAIL_PROVIDER=resend`, `CEKRIR_RESEND_API_KEY`, and `CEKRIR_RESEND_FROM` in `apps/backend/.env`. Set `CEKRIR_VERIFICATION_URL` to the public verification-page URL. Use a verified sending domain; never commit the API key. Delivery uses the official Resend Python SDK and keeps the existing idempotency keys. The existing SMTP provider remains available. The verification email is sent during registration; a welcome email is attempted after successful email verification. Until Resend is configured, automatic location email is skipped and requests requiring email delivery report that it is unavailable.

For package notifications, the main API snapshots the mapped camera's location when a detection notification is created through `/api/v1/detections` or `/api/v1/detections/frame`. It sends to the location admin and members whose database accounts are active and email-verified, with one email per user. A camera must be assigned to a location before its detections can generate location emails. Notifications for unassigned cameras do not send email. The separate camera-preview server's `/camera/frame` only displays JPEGs and does not perform package detection or trigger these emails. The existing shared ingestion key does not authenticate an individual camera: someone with that key can claim a different camera ID, so per-device credentials are needed before relying on this mapping across untrusted devices.

The individual email endpoint allows an admin to send to themselves or to an active, verified member of an owned location. Use a unique `Idempotency-Key` for each new message; Resend uses the derived per-user key to deduplicate retries for 24 hours. Email is sent synchronously and a successful response means the provider accepted the request, not that it reached the recipient. Package and welcome emails are best-effort: failures are logged and are not queued for retry. The existing in-app notification list and Redis WebSocket are not yet scoped by location; the location restriction described here applies to email.

### Screenshot autofill

Send the original screenshot bytes with `Content-Type: image/png`, `image/jpeg`, or `image/webp`. The image must be static, at most 5 MiB, and at most 20 megapixels. The endpoint returns `200` with the fields below when analysis completes, including when some fields are unreadable. Results are for review only. Cekrir does not persist the image or this response.

```json
{
  "resi_number": "000Example12",
  "courier_service": "SPX Express",
  "sender_name": null,
  "product_names": ["Storage box"]
}
```

Unreadable text fields return `null` and unavailable products return `[]`. Errors use `413` for an oversized body, `415` for an unsupported media type, `422` for an invalid image, `502` for invalid provider output, `503` for an unavailable or unconfigured provider, and `504` for a provider timeout.

Set `CEKRIR_OPENAI_API_KEY` in the backend environment and optionally set `CEKRIR_SCREENSHOT_MODEL` to a model that supports images and structured output. The default is `gpt-6-luna`. The backend sends the screenshot to OpenAI with `store: false` and a 25-second provider deadline. When the API is behind Nginx, apply the screenshot route block from [the proxy template](../../deploy/nginx/cekrir.conf) to the active API server, including its HTTPS configuration.

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
