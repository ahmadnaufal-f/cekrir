# Vercel frontend deployment

The tables below record the original npm-based releases. Current builds use the pinned pnpm 11 version and commands in [vercel.json](../../vercel.json); see [tooling.md](../tooling.md) for the migration.

## GitHub-connected deployment

The owner's later request changed the deployment source from local artifacts to GitHub. The frontend and repository-root [vercel.json](../../vercel.json) were committed and pushed to [`frontend/household-vercel`](https://github.com/ahmadnaufal-f/cekrir/tree/frontend/household-vercel). `main` remains at the original baseline; no merge was performed.

| Field                  | Git deployment result                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| Canonical project URL  | https://cekrir-frontend.vercel.app                                                                            |
| Existing URL           | https://cekrir.vercel.app currently aliases this Git-built deployment                                         |
| Immutable deployment   | https://cekrir-frontend-mj8fblll9-ahmadnaufals-projects.vercel.app                                            |
| Target / status        | Production / READY                                                                                            |
| Project                | `cekrir-frontend` (`prj_ZIQ9c9yjVMybd4XGcmQqvzg2E8xn`)                                                        |
| Repository             | `ahmadnaufal-f/cekrir` (GitHub repo ID `1456573310`)                                                          |
| Source branch / commit | `frontend/household-vercel` / `08b64ecf827600e44e7c198c5f3c4d69ec4efcb8`                                      |
| Deployment ID          | `dpl_7Xeha3HEKTfFXy725jfWHb5u264T`                                                                            |
| Build                  | Repository root, Node 24, `npm ci`, `npm run build --workspace @cekrir/frontend`; output `apps/frontend/dist` |

The existing artifact-only project's connector could not attach Git, and the local Vercel CLI had no authenticated session. A new Git-linked project was created through the connected Vercel app. Its GitHub association was confirmed with the repository-filtered project query. The deployment log explicitly reports cloning the branch and commit above, followed by a successful install, Vue typecheck, and Vite build. Local frontend check, 53 tests, and build also passed before publication.

Automatic approval review rejected pushing the whole change directly to the default `main` branch. The separate frontend branch was used as a safer, reviewable alternative. There was no force push or change to `main`, backend, firmware, schema, or lockfile.

Vercel's standard Git setup uses `main` for automatic production releases and feature branches for previews. This production release was explicitly created from the frontend branch. Review and merge that branch before relying on future `main` production builds to include these frontend changes. Merging was not part of this work.

Use `cekrir-frontend.vercel.app` as the project's automatically managed production domain. `cekrir.vercel.app` was reassigned to this deployment, but its project-domain registration remains on the old artifact project; automatic domain migration was rejected as already assigned. Moving that domain's registration in the Vercel dashboard is needed if it must automatically follow every future production release. The old artifact project remains available as a rollback reference.

Default deployment protection and the production mock guards were retained. Live backend integrations remain unavailable. No backend hosting, native push, custom domain purchase, or authentication provider was added.

## Original artifact deployment

Deployed on 2026-11-15 following the owner's request to deploy on Vercel.

| Field                | Result                                                                                                                  |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| URL                  | https://cekrir.vercel.app                                                                                               |
| Immutable deployment | https://cekrir-obr0lg8qy-ahmadnaufals-projects.vercel.app                                                               |
| Target / status      | Production / READY                                                                                                      |
| Team                 | `ahmadnaufals-projects` (`team_ECbg9Rn1rC7bPPvPjKSt7HUj`)                                                               |
| Project              | `cekrir` (`prj_j7Ku8FepocpdE2AwiYtfjnx2POAk`)                                                                           |
| Deployment           | `dpl_DLbGV9uMXLt1X6j5NpB3APecmVge`                                                                                      |
| Source               | Local modified working tree based on `bc45600de0906a4b7995ac71118025259072c8a5`; changes have not been pushed to GitHub |
| Framework            | Vue/Vite frontend, deployed as static build output                                                                      |
| Node                 | Local build and Vercel project configured for Node 24                                                                   |
| Vercel build         | Completed; build log reports 43ms for packaging the already-built static files                                          |

There was no existing Cekrir Vercel project. A new project was created in the connected owner's sole team, then the four files from `apps/frontend/dist` were uploaded through the authenticated Vercel connector and deployed. `npm run build` passed immediately before upload. The backend, firmware, database, and native app were not deployed.

Vercel's default deployment protection was retained, so viewing the stable URL may require signing in with the authorized Vercel account. No custom domain or access-control relaxation was configured. The build uses the existing production behaviour: development mocks and demo login credentials are excluded; live household integrations remain unavailable. Deploying the frontend does not supply auth, household APIs, photos, tracking, or native push.

## Verification

- Vercel reported `READY`, target `production`, with no alias error.
- Authenticated HTTP checks returned 200 for HTML, JavaScript, CSS, and favicon. All four response bodies exactly matched the local production artifacts.
- Chromium rendered the deployed login and explicit live-integration-unavailable state at 390×844, with no page errors or failed requests. No demo login hint or simulator controls appeared.
- Browser access used a temporary Vercel share link. The local automation environment did not trust its HTTPS interception certificate, so certificate validation was disabled only in that browser test context. Vercel connector fetches also verified the deployed files independently. No Vercel protection or application TLS setting was changed.
- The error/fatal runtime-log query returned no records. This is a static deployment; it is not server-side integration or native push evidence.
- [Deployed mobile screenshot](screenshots/vercel-production-mobile.png).

This first release was an artifact deployment, not a Git-connected build. It has been superseded by the GitHub-connected project described above.

See [integration status](integration-status.md) and [backend/firmware gaps](backend-gaps.md) for the remaining capabilities and unresolved contracts.
