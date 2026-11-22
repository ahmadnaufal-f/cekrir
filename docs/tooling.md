# JavaScript tooling

Use Node 24 and the pinned pnpm 11.28.12 from `package.json#packageManager`. The workspace packages are declared in `pnpm-workspace.yaml`; commit `pnpm-lock.yaml` when JavaScript dependencies change. Python continues to use uv and `apps/backend/uv.lock`.

```sh
corepack enable
pnpm install --frozen-lockfile
pnpm run check:frontend
pnpm --filter @cekrir/frontend test
pnpm run build
```

Oxfmt 0.78.0 replaces the separate Prettier dependency, configuration, and commands. Its [migration command](https://oxc.rs/docs/guide/usage/formatter/migrate-from-prettier) preserved single quotes, no semicolons, trailing commas, 80-column lines, and the existing ignored backend/native/generated paths. Formatting the pnpm lockfile is left to pnpm; Alembic migrations and Ruff format the Python backend.

Oxlint 1.93.0 uses the [recommended configuration workflow](https://oxc.rs/docs/guide/usage/linter/quickstart): a committed config, default correctness rules as errors, the built-in TypeScript/Unicorn/Oxc rules, and Vue/Vitest plugins. CI fails on warnings. Browser and Node environments are scoped to their files. Vitest's explicit mock-type-parameter rule is disabled because the existing implementation callbacks infer their types; the other enabled correctness rules remain active. The route validator has one documented suppression because rejecting control characters is intentional.

Oxlint checks Vue script blocks. Keep `vue-tsc --noEmit` for Vue template and TypeScript verification; type-aware Oxlint is an optional separate dependency/mode and is not enabled by this setup.

| Command                    | Purpose                                                                   |
| -------------------------- | ------------------------------------------------------------------------- |
| `pnpm run lint`            | Oxlint, including Vue scripts and tests; fail on warnings                 |
| `pnpm run lint:fix`        | Apply Oxlint's safe fixes                                                 |
| `pnpm run format:check`    | Check formatting with Oxfmt                                               |
| `pnpm run format:frontend` | Format frontend source and HTML with Oxfmt                                |
| `pnpm run format`          | Format Python via Ruff and supported files via Oxfmt                      |
| `pnpm run check:frontend`  | Oxlint plus Vue/TypeScript checking, without backend/database setup       |
| `pnpm run check`           | Formatting, Oxlint, Alembic schema check, Ruff, and Vue/TypeScript checks |

The install-script allowlist uses pnpm 11's `allowBuilds` setting for the remaining native dependencies. Unlisted dependency build scripts retain pnpm 11's defaults. Native generated projects and build outputs are excluded from format/lint checks.

CI installs the version from `packageManager` with `pnpm/action-setup` and uses a frozen lockfile. Vercel invokes `corepack pnpm` explicitly for install/build so the pinned major is used without relying on the platform's default pnpm. Builds remain frontend-only; this does not deploy the backend or enable production mocks.

For editors, use the [official Oxc integration](https://oxc.rs/docs/guide/usage/linter/editors) for lint diagnostics and Oxfmt formatting. Existing historical deployment and implementation reports retain the actual npm/Prettier commands that were run before this migration.

## Migration verification

The frozen pnpm 11 install, `format:check`, `check:frontend`, all 53 frontend Vitest tests, and the production build passed during the prior frontend tooling update. The current backend database commands use Alembic; see [database setup](database.md) for migration and schema-check commands.

The backend now uses SQLAlchemy and Alembic with a Redis live-notification channel. Historical results above predate that backend change and do not verify its migrations or runtime behavior.
