# Local browser verification

These scripts exercise the actual Vue app against explicit in-memory fixtures; they do not verify backend, hardware, native push, or phone behaviour. Playwright is supplied by the verification runner, not added as an application dependency. Chromium must be available at `/usr/bin/chromium`.

Start a development server with `VITE_APP_MODE=mock npm run dev:frontend`. With Playwright available, run from the repository root:

```sh
node docs/frontend/verification/screenshots.cjs
node docs/frontend/verification/mock-flows.cjs
```

If the runner package is installed outside this repository, set `PLAYWRIGHT_MODULE` to its absolute module path. The implementation session used `/tmp/cekrir-npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright` after acquiring a temporary runner with `npm exec --yes --package=playwright -- playwright --version`. This path is environment-specific.

`screenshots.cjs` checks admin/member routes, independent resource states, photo URL release, keyboard skip-link focus, responsive layout and large text, and captures images into `../screenshots`. `mock-flows.cjs` mounts the same app with an injectable mock harness to exercise backend rejection, stale inventory, account/session transitions, notification navigation and image decode errors. It must run against local Vite development code; it does not add a simulator or test hook to the shipped application.

For production verification, build (including `VITE_APP_MODE=mock npm run build` to prove mock gating) and run `npm run preview --workspace @cekrir/frontend -- --port 4173`. Then:

```sh
node docs/frontend/verification/production.cjs
```

It verifies the unavailable live state, absence of demo hints/simulator controls, and rejection of fixture credentials. Never use real credentials in these scripts or captures. Current results and limitations are in [integration-status.md](../integration-status.md).
