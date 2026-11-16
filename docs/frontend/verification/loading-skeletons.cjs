// Loading-state checks against delayed, explicit in-memory service fixtures.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const path = require('node:path')

;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const page = await browser.newPage({
      viewport: { width: 390, height: 844 },
      locale: 'id-ID',
    })
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.goto('http://127.0.0.1:5173')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await page.evaluate(async () => {
      const source = await (await fetch('/src/App.vue')).text()
      const vuePath = source.match(/from ["']([^"']*vue\.js[^"']*)["']/)[1]
      const [{ createApp }, { default: App }, { createMockHarness }] =
        await Promise.all([
          import(vuePath),
          import('/src/App.vue'),
          import('/src/services/mock.ts'),
        ])
      document.querySelector('#app').__vue_app__.unmount()
      location.hash = '/login'
      window.harness = createMockHarness({ pageSize: 3 })
      window.listRequests = []
      window.totalsRequests = []
      const list = window.harness.services.deliveries.list
      const totals = window.harness.services.deliveries.totals
      window.harness.services.deliveries.list = async (...args) => {
        const result = await list(...args)
        return new Promise((resolve) =>
          window.listRequests.push(() => resolve(result)),
        )
      }
      window.harness.services.deliveries.totals = async (query) => {
        const result = await totals(query)
        return new Promise((resolve) =>
          window.totalsRequests.push(() => resolve(result)),
        )
      }
      createApp(App, { services: window.harness.services }).mount('#app')
    })
    await page
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await page.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await page
      .getByRole('heading', { name: 'Paket diterima', exact: true })
      .waitFor()
    await page.waitForFunction(
      () =>
        window.listRequests.length === 1 && window.totalsRequests.length === 1,
    )
    assert.equal(
      await page.locator('.delivery-summary__value-skeleton').count(),
      2,
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 3)
    assert.equal(await page.locator('.delivery-card').count(), 0)
    assert.equal(
      await page.getByText('Memuat ringkasan…', { exact: true }).count(),
      0,
    )
    await page.screenshot({
      path: path.resolve(
        __dirname,
        '../screenshots/package-loading-skeletons-mobile.png',
      ),
      fullPage: true,
      animations: 'disabled',
    })
    await page.evaluate(() => window.listRequests[0]())
    await page.waitForFunction(
      () => document.querySelectorAll('.delivery-card').length === 3,
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 0)
    assert.equal(
      await page.locator('.delivery-summary__value-skeleton').count(),
      2,
    )
    await page.evaluate(() => window.totalsRequests[0]())
    await page.waitForFunction(
      () =>
        document.querySelectorAll('.delivery-summary__value-skeleton')
          .length === 0,
    )
    await page
      .getByRole('button', { name: 'Muat pengiriman berikutnya', exact: true })
      .click()
    await page.waitForFunction(() => window.listRequests.length === 2)
    assert.equal(
      await page.locator('.delivery-card').count(),
      3,
      'existing cards stay available while the next page loads',
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 3)
    assert.equal(
      await page.locator('.delivery-summary__value-skeleton').count(),
      0,
    )
    await page.screenshot({
      path: path.resolve(
        __dirname,
        '../screenshots/package-pagination-skeletons-mobile.png',
      ),
      fullPage: true,
      animations: 'disabled',
    })
    await page.evaluate(() => window.listRequests[1]())
    await page.waitForFunction(
      () => document.querySelectorAll('.delivery-card').length === 6,
    )
    const focusedHref = await page
      .locator('.delivery-card')
      .first()
      .getAttribute('href')
    await page.locator('.delivery-card').first().focus()
    await page.evaluate(() =>
      document.dispatchEvent(new Event('visibilitychange')),
    )
    await page.waitForFunction(
      () =>
        window.listRequests.length === 3 && window.totalsRequests.length === 2,
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 6)
    assert.equal(await page.locator('.delivery-card').count(), 0)
    assert.equal(
      await page.locator('.delivery-summary__value-skeleton').count(),
      2,
    )
    await page.evaluate(() => window.listRequests[2]())
    await page.waitForFunction(
      (href) => document.activeElement?.getAttribute('href') === href,
      focusedHref,
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 0)
    await page.evaluate(() => window.totalsRequests[1]())
    await page.waitForFunction(
      () =>
        document.querySelectorAll('.delivery-summary__value-skeleton')
          .length === 0,
    )
    assert.deepEqual(errors, [])
    console.log(
      'PASS: summary/package skeletons on initial loading, independent completion, pagination placeholders with existing cards retained, refresh placeholders for loaded cards, no visible summary loading text, and keyboard focus restored after background refresh.',
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
