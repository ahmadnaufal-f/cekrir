# Frontend alignment and verification

> Update (2026-11-19): the active frontend now targets the merged shipment API. See [API integration and verification](api-integration.md) for current behavior and tests. The household prototype details below are historical; they are not claims about the active application.

Reviewed and implemented on 2026-11-15 against `bc45600de0906a4b7995ac71118025259072c8a5` (the fresh checkout matched the brief). No existing uncommitted work or repository `AGENTS.md` was present. The monorepo, lockfile, Vue/TypeScript/Vite/Capacitor/Vitest stack, app identity `id.cekrir.app`, and legacy shipment client remain. Backend, firmware, database schema, and tracked native files are unchanged. The initial implementation package did not deploy or merge anything; the owner's subsequent deployment request is recorded in [Vercel deployment](vercel-deployment.md).

**Verified level: frontend UI with explicit mocks.** This is not live frontend integration, Android phone validation, or the complete hardware demonstration. Canonical requirements and FE01–FE16 coverage are in [spec-map.md](spec-map.md); teammate dependencies and legacy API compatibility are in [backend-gaps.md](backend-gaps.md).

## Floating navigation and contextual guidance — 2026-11-16

The previous hamburger layout has been replaced by a floating bottom bar using Cekrir's palette and outline icons. Admins see **Paket**, **Perangkat**, and **Anggota**. Members retain delivery-only access; admin route guards remain enforced. Account and notification settings open from the top-right initials avatar. The brand and avatar stay at the top while scrolling and gain individual raised surfaces away from scroll position zero. Tight layouts and enlarged text use icons with accessible names. The page reserves space for the bar and restores the top/content focus on route changes.

Guidance is now contextual: missing ESP32 registration shows instructions beside its form; after registration, help loads on expansion. Camera help appears for missing, unselected, or incompletely configured cameras. First-member guidance appears only after a successful empty list response and focuses the existing form. Guide requests keep independent retry/authentication/stale-response handling. Old `/setup` links redirect to Devices. Firmware remains a scaffold and BARDI guidance remains pending validation. Public copy continues to use **lokasi penerimaan**; internal `householdId`/`householdName` contracts remain unchanged.

Verification includes 53 frontend tests, type check, production build, Oxfmt/Oxlint checks, browser navigation captures, and injected mock flows. Browser checks cover mobile, tablet, desktop, and 320px with 200% text, including scroll-state changes, keyboard navigation, avatar access, guide recovery and first setup. These UI changes add no live backend or native integration.

Previews: [mobile](screenshots/admin-navigation-mobile.png), [scrolled](screenshots/admin-navigation-scrolled-mobile.png), [tablet](screenshots/admin-navigation-tablet.png), [desktop](screenshots/admin-navigation-desktop.png), [large text](screenshots/admin-navigation-large-text.png), [first device setup](screenshots/first-device-guides-mobile.png), [first member](screenshots/first-member-guide-mobile.png).

## Delivered behaviour

- Common login and admin signup; member navigation and direct admin-route guards; household delivery list and exact-ID detail routes.
- Independent pending/ready/unavailable photo and tracking outcomes. The scanned resi and timestamp remain visible on partial failure. Missing optional tracking fields are omitted.
- Admin device inventory, first ESP32 registration with a dismissible one-time mock credential, multiple cameras, one selected delivery camera, and preservation of prior state after failed mutations.
- Admin-created member accounts without replacing the admin session; local completion secrets clear on dismissal or leaving the screen.
- ESP32 source/guide references to the reviewed repository revision; honest pending BARDI guide. No camera discovery, stream playback, provisioning, compilation, or flashing in the app.
- Push transport boundary, permission and backend-association states, validated event/tap handling, early tap retention, foreground banners, deduplication, household checks, token refresh races, and logout/detach handling. Uncertain token association blocks silent account reassociation.
- Obsolete request results are ignored, account-scoped screens reset, and photo object URLs are revoked on replacement/unmount or image-decode failure.

## Operation status

| Operation                                       | Development mock                                                                        | Live status                                                                                                                     |
| ----------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Login, signup, session restoration              | Synthetic admin/member/second-household accounts; new signup creates an empty household | Backend has basic JWT register/login, but frontend session persistence, household creation, and DTO agreement are not connected |
| Delivery list/detail and household scope        | Shared in-memory repository, cursor paging, all nine photo/tracking combinations        | Unavailable; legacy shipments do not supply delivery events or ownership                                                        |
| Delivery photo                                  | Labelled SVG illustration returned through the photo service as a Blob                  | Unavailable; no authorized BARDI photo route. Authenticated-byte transport is unit-tested with synthetic responses only         |
| Devices and selected camera                     | Shared inventory, one-ESP32 limit, several cameras, failure injection                   | Unavailable; ownership, provisioning, write-only credentials, and selection APIs remain drafts                                  |
| Member creation and login                       | Shared fixture accounts; admin session retained                                         | Backend supports member registration and admin role updates, but household invites and the frontend flow are not connected      |
| Setup content                                   | Service returns allowlisted real source/guide references and pending BARDI content      | Source material exists; neither guide is physically validated. No live setup API is connected                                   |
| Push permission, token upsert/detach, event/tap | Simulated bridge and fixture association; lifecycle and race tests                      | Unavailable; no native transport/provider or live installation API configured                                                   |
| Legacy shipment/feed API                        | Existing client preserved separately                                                    | Existing `/api/v1` scaffold semantics only; not exercised as household integration                                              |

Live operations return explicit `integration_unavailable` errors rather than attempting draft endpoints or synthesizing ownership. The transport helper provides bounded 15-second requests, bearer-byte fetching, status/field errors, and `Retry-After` backoff for future agreed adapters. It is not evidence that a live auth or photo endpoint exists.

## Run the frontend review

From the repository root:

```sh
pnpm install --frozen-lockfile
VITE_APP_MODE=mock pnpm run dev:frontend
```

Open `http://127.0.0.1:5173`. Development credentials are `admin@demo.test` / `demo1234` and `anggota` / `demo1234`. `tetangga` uses the same mock password for another-household checks. These are fake test accounts. New fixture accounts and inventory changes survive navigation but not a page reload.

Without the explicit development setting, the app defaults to live mode and shows missing integration. Production ignores `VITE_APP_MODE=mock`. The fixture module, demo login credentials/hint, fixture deliveries, and simulated token were checked absent from the production JavaScript. Live failures never fall back to mocks.

## Historical implementation verification results

These commands record the original npm/Prettier run. The current package-manager and quality-tool setup is documented in [tooling.md](../tooling.md).

Environment: Node `v24.22.1`, npm `11.9.0`, Linux Chromium, compatible Capacitor 8 dependencies from the unchanged root lockfile.

| Command or check                                | Observed result                                                                                                                                                                                                                                                                                                |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm ci`                                        | Passed; 318 packages installed                                                                                                                                                                                                                                                                                 |
| `npm run check --workspace @cekrir/frontend`    | Passed                                                                                                                                                                                                                                                                                                         |
| `npm run test --workspace @cekrir/frontend`     | Passed: 53 tests in five files, including legacy API tests, routes, mock invariants, live transport failures/backoff, and push lifecycle/races                                                                                                                                                                 |
| `npm run build`                                 | Passed, Vue typecheck and Vite production build                                                                                                                                                                                                                                                                |
| `VITE_APP_MODE=mock npm run build`              | Passed; production still selects live mode. Bundle audit excludes fixture accounts/passwords, fixture delivery markers, and simulated token                                                                                                                                                                    |
| `npm run cap:sync --workspace @cekrir/frontend` | Passed for Android, iOS, and web assets; existing local-notifications plugin only. This does not build an APK or establish iOS support                                                                                                                                                                         |
| Targeted Prettier check                         | Passed for frontend source, HTML, frontend docs/check scripts, and README                                                                                                                                                                                                                                      |
| Browser screenshots and navigation              | Passed at 390×844 mobile, 1280×900 desktop, and delivery list at 320px with 200% text; no page errors or horizontal overflow in the captured states                                                                                                                                                            |
| Browser fault-injected flows                    | Passed: secret dismissal, stale second-ESP32 rejection, failed camera selection preserving state, multiple cameras, member creation/login, foreground notification without automatic navigation, exact-ID banner tap, 401 reauthentication retaining ID, 403/404, and image decode failure preserving tracking |
| Production browser check                        | Passed: live unavailable state, no demo hint or simulator, fixture login rejected without successful mock fallback                                                                                                                                                                                             |
| Independent Luna finish review                  | One misleading unavailable-photo caption was corrected and recaptured; reviewer scored the fix resolved, disposition `ship` for that correction. No native evidence was claimed                                                                                                                                |

The first local server attempt lacked permission to listen; it was restarted successfully with network permission. Intermediate integration type errors, a large-text list-header overflow, and a retained demo login hint in the production bundle were corrected before the results above. Root backend/database tests were not run for this frontend-only package.

The browser checks are retained in [verification](verification/README.md). They use temporary Playwright runner tooling and installed Chromium, with no app dependency or lockfile change. Unit tests use the repository's existing Vitest.

## Screenshots

All content is synthetic except the production unavailable-state interface. No one-time device/member completion secrets were exported.

| State                                    | Capture                                                                                                                                                                   |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Common login                             | [Mobile](screenshots/login-mobile.png)                                                                                                                                    |
| Admin deliveries                         | [Mobile](screenshots/admin-deliveries-mobile.png)                                                                                                                         |
| Complete delivery                        | [Mobile](screenshots/delivery-complete-mobile.png)                                                                                                                        |
| Photo unavailable, tracking retained     | [Mobile](screenshots/delivery-photo-unavailable-mobile.png)                                                                                                               |
| Tracking unavailable, photo retained     | [Mobile](screenshots/delivery-tracking-unavailable-mobile.png)                                                                                                            |
| Both unavailable                         | [Mobile](screenshots/delivery-failures-mobile.png)                                                                                                                        |
| Pending photo and tracking               | [Mobile](screenshots/delivery-pending-mobile.png)                                                                                                                         |
| Device inventory                         | [Mobile](screenshots/devices-mobile.png)                                                                                                                                  |
| Members and creation form                | [Mobile](screenshots/members-mobile.png)                                                                                                                                  |
| Setup readiness                          | [Mobile](screenshots/setup-mobile.png)                                                                                                                                    |
| Account and simulated notification setup | [Mobile](screenshots/settings-mobile.png)                                                                                                                                 |
| Member navigation                        | [Mobile](screenshots/member-deliveries-mobile.png), [desktop](screenshots/member-deliveries-desktop.png), [320px/200% text](screenshots/member-deliveries-large-text.png) |
| Production unavailable state             | [Mobile](screenshots/live-unavailable-mobile.png)                                                                                                                         |

## Decisions and remaining validation

Bahasa Indonesia copy, hash navigation without a new router dependency, memory-only credentials/installation metadata, 15-second transport timeout, bounded notification queues, and prototype form fields are reversible implementation defaults. Notification IDs currently accept bounded opaque alphanumeric/`.`/`_`/`:`/`-` strings rather than assuming UUIDs; reconcile accepted characters with the eventual payload contract. A frontend role guard or fixture authorization is not server security.

Still unresolved for frontend integration: token refresh and secure persistence, household endpoint/DTO agreement, native push plugin/provider and client/server configuration, persistent installation identity, photo access/storage/retention, validated BARDI connection/guide, shipping provider and final courier, reachable HTTPS phone access, scanner board/sensor/wiring, and retry/deduplication policies. The backend now has basic member/admin JWT endpoints and SQLAlchemy/Alembic persistence, but frontend authentication, household ownership, and push are not connected.

If the official push candidate is chosen, it needs a Capacitor-8-compatible `@capacitor/push-notifications` dependency, owner-provided Android Firebase configuration for `id.cekrir.app`, channel/icon agreement, backend sending credentials kept off the client, and agreed installation upsert/detach endpoints. None was silently selected or fabricated.

Java 21 is present, but `adb`, `sdkmanager`, physical phone, selected push configuration, and real backend contracts were unavailable. No APK, phone install, real OS permission, foreground/background/process-cold-start delivery, Android back/resume behaviour on a phone, protected real photo, CCTV connection, tracking-provider lookup, or ESP32 scan was verified. Existing iOS files and a successful asset sync do not certify iOS support.

## Skills and delegation

Both requested skills were installed and read from upstream into `/workspace/skills`: `impeccable` from `pbakaus/impeccable` at `2b86d9c07b97d4bed7de23583e1bd1e58dd2baae`, and `vue-best-practices` from `vuejs-ai/skills` at `198f0cd8f7f9c0a3d9b566ccc16de6677519ee78`. Impeccable's context launcher could not install its engine in the restricted home cache; existing project context and its design references were read directly instead. The skills' UI/Vue guidance was applied; confirmed specifications governed conflicts.

Six independent agents used the available `gpt-6-luna` model with `xhigh` reasoning: deliveries, admin/setup, mock services, push lifecycle, boundary tests/handoff, and independent review. Shared types/services were established first, implementation files had separate ownership, and integration, fault-injected browser checks, builds, sync, and final verification stayed with the main agent. No model or reasoning substitution was necessary.
