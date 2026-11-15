// Local browser verification tool; Playwright is supplied by the runner, not an app dependency.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const page = await browser.newPage({
      viewport: { width: 390, height: 844 },
    })
    const errors = []
    page.on('pageerror', (e) => errors.push(e.message))
    await page.goto('http://127.0.0.1:4173')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await page
      .getByText('Mode live · integrasi belum tersedia', { exact: true })
      .waitFor()
    assert.equal(await page.getByText(/admin@demo.test/).count(), 0)
    assert.equal(
      await page.getByRole('button', { name: /Simulasikan/ }).count(),
      0,
    )
    await page
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await page.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await page
      .getByRole('alert')
      .filter({ hasText: 'Integrasi rumah tangga belum tersedia.' })
      .waitFor()
    assert.equal(
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .count(),
      0,
    )
    await page.screenshot({
      path: require('node:path').resolve(
        __dirname,
        '../screenshots/live-unavailable-mobile.png',
      ),
      fullPage: true,
    })
    assert.deepEqual(errors, [])
    console.log(
      'PASS: production forced mock env still live; no demo hint/simulator, mock login rejected with integration unavailable, no page errors.',
    )
  } finally {
    await browser.close()
  }
})().catch((e) => {
  console.error(e)
  process.exitCode = 1
})
