# Vercel frontend deployment

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

This was an artifact deployment, not a Git-connected build. Future GitHub pushes will not automatically publish these uncommitted changes. To release a later snapshot, rebuild the frontend and deploy its current output to this existing project, or explicitly configure Git deployment separately.

See [integration status](integration-status.md) and [backend/firmware gaps](backend-gaps.md) for the remaining capabilities and unresolved contracts.
