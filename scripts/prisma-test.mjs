import 'dotenv/config'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const testUrl = process.env.TEST_DATABASE_URL
if (!testUrl)
  throw new Error(
    'Set TEST_DATABASE_URL in the root .env before running API tests.',
  )
const parsed = new URL(testUrl)
if (
  !['postgres:', 'postgresql:'].includes(parsed.protocol) ||
  !parsed.pathname.endsWith('_test')
) {
  throw new Error(
    'TEST_DATABASE_URL must point to a PostgreSQL database ending in _test.',
  )
}
if (process.env.DATABASE_URL) {
  const app = new URL(process.env.DATABASE_URL)
  if (app.host === parsed.host && app.pathname === parsed.pathname) {
    throw new Error(
      'The test database must be separate from the application database.',
    )
  }
}

const result = spawnSync(
  process.execPath,
  [
    fileURLToPath(
      new URL('../node_modules/prisma/build/index.js', import.meta.url),
    ),
    'migrate',
    'deploy',
  ],
  { stdio: 'inherit', env: { ...process.env, DATABASE_URL: testUrl } },
)
if (result.error) throw result.error
process.exit(result.status ?? 1)
