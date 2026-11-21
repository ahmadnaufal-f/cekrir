# Frontend API integration

The active Vue application targets the API merged in PR #7 at `2083891025c3139dbb4776dc908ca75eff6854bb`. Contract sources: [API guide](../../apps/backend/API.md), [OpenAPI](../../apps/backend/api/openapi.json), and the backend request validators (including normalization and UTF-8 password limits).

## Supported flows

- Register a **member** using full name, email and password; show verification-pending instructions. Confirm on the backend's emailed HTML page, then return to sign in. Resend asks for credentials and shows the backend's generic outcome. A registration 503 may mean the account already exists: resend or sign in rather than automatically submitting registration again.
- Login returns the user and a token pair. Tokens stay in memory, with one shared refresh operation before expiry or a single retry after protected 401. Failed refresh authentication signs out; a connection failure keeps the session available for retry. Public auth failures do not trigger token refresh. Logout clears local state and closes sockets; the backend has no logout/revocation endpoint.
- Browse shared shipments with status, tracking history, and creation, detection, and check timestamps. Admins can explicitly refresh tracking. Provider `demo` is labelled as sample data.
- Browse package cards with today and all-time totals, resi or courier search, loading states, and touch pull-to-refresh. The current API exposes offset pages, so the frontend loads the remaining pages in the background for complete totals and search. Today uses the device's calendar date and the shipment's creation time.
- Receive foreground package reports over WebSocket. Tap a report to open its shipment detail. Reconnecting or resuming refreshes the shipment view. The client deduplicates event IDs and pauses the socket in the background. It rotates the socket with access tokens, backs off up to 30 seconds, and keeps HTTP browsing available after a Redis failure.
- Admins list API users and confirm role changes. A location conflict (409) leaves the row unchanged. Self-demotion updates session identity, removes management access immediately and refreshes the token pair.

Active routes are `#/shipments`, `#/shipments/:id`, `#/settings`, and the admin-only `#/members`, `#/devices`, `#/devices/setup/esp32`, and `#/devices/setup/cameras`. The Devices tabs link to illustrated ESP32 and BARDI setup guides. Device registration and selecting a delivery camera run in development demo mode. The live tabs show setup guidance while device management awaits API support. Old `#/deliveries` links map to shipments. The old `#/notifications` route falls back to the shipment list. There is no GET shipment-by-ID endpoint: uncached detail links search offset pages until found/exhausted, and are cancellable. A fresh detail reload bypasses the snapshot cache. Large lists can make uncached links slow; offset pagination can shift under concurrent inserts. IDs are deduplicated, but the frontend does not claim snapshot-consistent history.

## Architecture and boundaries

`src/features/api/` contains wire DTOs, the HTTP/session client, notification connection lifecycle, route parser, and the API-compatible development mock. `src/features/` contains the active screens. `App.vue` owns session-aware navigation and foreground notifications. Legacy shipment helpers share the active client's session. The prior household components/services remain unmounted as historical prototype code; their tests do not establish household integration.

The backend records and user list are **shared**, not household-scoped. The active UI does not fabricate household IDs, delivery photos, device registration, member creation, camera previews, payment processing, or push-installation endpoints. The detection endpoints remain scanner/backend integrations; ingestion keys are never placed in frontend configuration. Existing user permissions are enforced by the backend; client role guards only control presentation.

## Running and deployment

Use the repository database/backend setup, including committed Alembic migrations. Configure SMTP, a verification URL and the bootstrap administrator in backend settings. The frontend runs with `pnpm run dev:frontend`.

- Development: `VITE_API_BASE_URL=/api/v1`; Vite forwards HTTP and WebSocket upgrades to port 8000.
- Hosted frontend/native builds: set an absolute, reachable HTTPS URL ending in `/api/v1`; allow the frontend origin in backend CORS and enable WebSocket upgrades on the API host. The static Vercel frontend configuration does not proxy API requests.
- No secrets belong in Vite variables. Browser WebSockets require query-token authentication with this API; avoid logging their URLs. Client socket rotation does not fix the backend's missing authorization rechecks for arbitrary long-lived clients.
- Reloading the page or restarting the app requires signing in again. No native secure-storage dependency was added.
- Development demo: `VITE_APP_MODE=mock pnpm run dev:frontend`; `admin@demo.test` or `member@demo.test`, password `demo12345678`. Demo registration stays pending and sends no mail. Production ignores mock mode and excludes both new and historical fixtures.

## Verification — 2026-11-19

Verified in headless Chromium against the actual FastAPI app, isolated PostgreSQL 17 and Redis 7, and a local SMTP mailbox. The SMTP sink accepted messages without sending external email. No backend or firmware implementation changes were required.

| Boundary                                                     | Observed result                                                                          |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Registration → PostgreSQL → SMTP → verification HTML → login | Passed with a newly registered member and real single-use email confirmation             |
| Admin shipment creation → PostgreSQL → member HTTP detail    | Passed; normalized resi/courier and stored history rendered                              |
| PostgreSQL notification → Redis → member browser feed        | Passed; WebSocket forwarding in Vite fixed during this check                             |
| Admin role promotion/demotion and self-demotion              | Passed; user rows updated and admin navigation disappeared after self-demotion           |
| Tracking-provider failure                                    | Injected HTTP 502 showed actionable error and retained form input                        |
| Logout and reload                                            | Passed; sign-in required again and account state cleared                                 |
| Mobile/desktop rendering                                     | Checked at 390×844 and 1365×900; no mobile horizontal overflow or browser runtime errors |

Screenshots: [mobile shipment detail](screenshots/api-integration-mobile.png), [desktop user management](screenshots/api-integration-desktop.png).

Automated frontend coverage includes concurrent refresh, rejected refresh, one-retry limits, logout races, self-demotion, registration validation, duplicate creation, paginated detail lookup, errors, notification deduplication, token renewal, Redis reconnect and background/resume. The historical household/push tests remain separate from this evidence.

Not verified: physical Android/iOS behavior, remote HTTPS deployment, external SMTP delivery, a real courier provider, or real camera hardware. Payment drafts, standalone camera viewing and background push are deferred. No deployment or GitHub write was performed for this implementation.

Check results: **82 frontend tests passed**, Vue/TypeScript check and production build passed, Oxlint passed, changed-file formatting and `git diff --check` passed. A production-bundle inspection found neither API demo records nor historical household fixtures. A separate browser run verified mock login, shipments, notification history, user listing, logout and verification-pending registration with no API network requests or runtime errors.

The repository-wide `pnpm run format:check` remains blocked by pre-existing formatting in `apps/esp32/README.md`, `docs/backend-deployment.md`, `docs/payments.md`, and `docs/tooling.md`; these files were not changed. The backend's existing CI database provisioning and legacy API-test issues are outside this frontend implementation.
