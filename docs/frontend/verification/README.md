# Local browser verification

These scripts exercise the actual Vue app against explicit in-memory fixtures; they do not verify backend, hardware, native push, or phone behaviour. Playwright is supplied by the verification runner, not added as an application dependency. Chromium must be available at `/usr/bin/chromium`.

Start a development server with `VITE_APP_MODE=mock pnpm run dev:frontend`. With Playwright available, run from the repository root:

```sh
node docs/frontend/verification/screenshots.cjs
node docs/frontend/verification/mock-flows.cjs
node docs/frontend/verification/package-page.cjs
node docs/frontend/verification/pull-refresh.cjs
node docs/frontend/verification/loading-skeletons.cjs
node docs/frontend/verification/delivery-search.cjs
```

If the runner package is installed outside this repository, set `PLAYWRIGHT_MODULE` to its absolute module path. The implementation session used `/tmp/cekrir-npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright` after acquiring a temporary runner with `npm exec --yes --package=playwright -- playwright --version`. This path is environment-specific.

`screenshots.cjs` checks admin/member routes, independent resource states, photo URL release, keyboard skip-link focus, the floating three-item admin navigation, avatar account access, flat/scrolled header states, desktop/tablet layouts, and 320px screens with large text. It also checks the location-name field and captures images into `../screenshots`. `mock-flows.cjs` mounts the same app with an injectable mock harness to exercise backend rejection, stale inventory, account/session transitions, notification navigation, image decode errors, first-member guidance, and independent contextual device guides. It checks guide retries, help after registration, and guide removal after configuration. It must run against local Vite development code; it does not add a simulator or test hook to the shipped application.

`package-page.cjs` uses a three-item mock page and a fixed UTC clock to verify full-location totals, compact resource pills, individual cards, midnight rollover, summary errors/retry, malformed counts, stale account responses, and expired sessions. It captures the package page at mobile, desktop, and enlarged-text sizes. Neither totals nor resource availability verifies live backend/hardware integration.

`pull-refresh.cjs` uses Chromium CDP touch input to test pull direction/threshold, cancellation, multi-touch, normal scrolling, click suppression, combined list/totals completion, a superseding resume refresh, failures, and desktop browser reload. `touch.cjs` is the shared input helper. This is synthesized Chromium touch evidence, not a physical phone, APK, or WebKit check. Desktop has no in-app refresh button; browser reload remains available. The existing development mock session resets on a full browser reload.

`loading-skeletons.cjs` delays the mock list/totals responses to verify initial, refresh, and pagination placeholders, independent completion, absence of visible summary loading text, and keyboard focus recovery. The pull runner also checks that only one refresh status is visible.

`delivery-search.cjs` verifies the combined mobile subtitle, empty and single-delivery locations, conditional search, matches beyond the first page, filtered pagination, literal queries, clear-button keyboard/focus behavior, out-of-order searches, rapid edits, filtered pull refresh, unfiltered totals, and responsive layouts. It mounts only explicit fixtures in development; it does not verify a live search endpoint.

For production verification, build (including `VITE_APP_MODE=mock pnpm run build` to prove mock gating) and run `pnpm --filter @cekrir/frontend preview --port 4173`. Then:

```sh
node docs/frontend/verification/production.cjs
```

It verifies the unavailable live state, absence of demo hints/simulator controls, and rejection of fixture credentials. Never use real credentials in these scripts or captures. Current results and limitations are in [integration-status.md](../integration-status.md).
