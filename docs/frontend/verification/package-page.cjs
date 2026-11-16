// Local UI verification against explicit fixtures; Playwright is runner tooling.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const path = require('node:path')
const { pullRefresh } = require('./touch.cjs')

;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      timezoneId: 'UTC',
      hasTouch: true,
      locale: 'id-ID',
    })
    const page = await context.newPage()
    const touch = await context.newCDPSession(page)
    const errors = []
    page.on('pageerror', (e) => errors.push(e.message))
    await page.clock.install({ time: new Date('2026-11-15T12:00:00Z') })
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
      window.originalTotals = window.harness.services.deliveries.totals
      createApp(App, { services: window.harness.services }).mount('#app')
    })
    async function login(id = 'admin@demo.test') {
      await page.getByLabel('Identitas masuk', { exact: true }).fill(id)
      await page.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
      await page.getByRole('button', { name: 'Masuk', exact: true }).click()
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .waitFor()
    }
    async function totals(today, allTime) {
      await page.waitForFunction(
        ({ today, allTime }) => {
          const text = (selector) =>
            document.querySelector(selector)?.textContent.replace(/\s/g, '')
          return (
            text('.delivery-summary__today') === today + 'paket' &&
            text('.delivery-summary__all-time') === allTime + 'paket'
          )
        },
        { today, allTime },
      )
    }
    async function capture(name, fullPage = false) {
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.mouse.move(0, 0)
      await page.screenshot({
        path: path.resolve(__dirname, '../screenshots/' + name + '.png'),
        fullPage,
        animations: 'disabled',
      })
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
        'no overflow: ' + name,
      )
    }
    await login()
    const cards = page.locator('.delivery-card')
    await cards.first().waitFor()
    assert.equal(await cards.count(), 3)
    await totals(9, 9)
    assert.equal(
      await page.locator('.delivery-summary .delivery-card').count(),
      0,
      'summary is independent of package cards',
    )
    assert.equal(
      await page.getByText('Waktu pemindaian', { exact: true }).count(),
      0,
    )
    assert.equal(
      await cards.first().locator('time').getAttribute('datetime'),
      '2026-11-15T08:50:00.000Z',
    )
    await capture('package-page-mobile')
    const more = page.getByRole('button', {
      name: 'Muat pengiriman berikutnya',
      exact: true,
    })
    await more.click()
    await page.waitForFunction(
      () => document.querySelectorAll('.delivery-card').length === 6,
    )
    await totals(9, 9)
    await more.click()
    await page.waitForFunction(
      () => document.querySelectorAll('.delivery-card').length === 9,
    )
    assert.equal(await page.locator('.delivery-resource-state').count(), 18)
    for (const state of ['ready', 'pending', 'unavailable']) {
      const badges = page.locator('.delivery-resource-state--' + state)
      assert.ok((await badges.count()) > 0)
      assert.ok(await badges.first().getAttribute('aria-label'))
      assert.ok(await badges.first().getAttribute('title'))
      assert.equal(
        await badges.first().locator('svg').getAttribute('aria-hidden'),
        'true',
      )
      assert.equal(
        await badges
          .first()
          .evaluate((el) => getComputedStyle(el).borderRadius),
        '999px',
      )
    }
    const loadingIcon = page
      .locator('.delivery-resource-state--pending svg')
      .first()
    assert.notEqual(
      await loadingIcon.evaluate((el) => getComputedStyle(el).animationName),
      'none',
    )
    await page.emulateMedia({ reducedMotion: 'reduce' })
    assert.equal(
      await loadingIcon.evaluate((el) => getComputedStyle(el).animationName),
      'none',
    )
    await page.emulateMedia({ reducedMotion: 'no-preference' })
    await capture('package-cards-mobile', true)
    await cards.first().focus()
    await page.keyboard.press('Enter')
    await page
      .getByRole('heading', { name: 'Rincian pengiriman', exact: true })
      .waitFor()
    await page
      .getByRole('button', { name: 'Kembali ke daftar', exact: true })
      .click()
    await totals(9, 9)
    await page.setViewportSize({ width: 1280, height: 900 })
    await capture('package-page-desktop')
    await page.setViewportSize({ width: 320, height: 800 })
    const largeText = await page.addStyleTag({
      content: 'html{font-size:200%}',
    })
    await capture('package-page-large-text', true)
    await largeText.evaluate((el) => el.remove())
    await page.setViewportSize({ width: 390, height: 844 })
    await page.clock.fastForward(12 * 60 * 60 * 1000 + 1000)
    await totals(0, 9)
    assert.equal(
      await page.locator('.delivery-summary time').getAttribute('datetime'),
      '2026-11-16',
    )
    await page.evaluate(() => {
      window.harness.services.deliveries.totals = async () => {
        throw new Error('mock totals failure')
      }
    })
    await pullRefresh(page, touch)
    await page
      .getByText('Ringkasan paket belum dapat dimuat.', { exact: true })
      .waitFor()
    assert.ok(
      (await cards.count()) > 0,
      'summary failure keeps the package list usable',
    )
    assert.match(
      await page.locator('.delivery-summary__all-time').innerText(),
      /—/,
    )
    await capture('package-summary-error-mobile')
    await page.evaluate(() => {
      window.harness.services.deliveries.totals = window.originalTotals
    })
    await page
      .getByRole('button', { name: 'Coba muat ringkasan lagi', exact: true })
      .click()
    await totals(0, 9)
    await page.evaluate(() => {
      window.harness.services.deliveries.totals = async (query) => ({
        ...query,
        receivedToday: 10,
        receivedAllTime: 1,
      })
    })
    await pullRefresh(page, touch)
    await page
      .getByText('Ringkasan paket belum dapat dimuat.', { exact: true })
      .waitFor()
    await page.evaluate(() => {
      window.harness.services.deliveries.totals = (query) =>
        new Promise((resolve) => {
          window.resolveOldTotals = () =>
            resolve({ ...query, receivedToday: 777, receivedAllTime: 999 })
        })
    })
    await page
      .getByRole('button', { name: 'Coba muat ringkasan lagi', exact: true })
      .click()
    await page
      .getByRole('link', {
        name: 'Buka akun dan notifikasi: Admin Demo',
        exact: true,
      })
      .click()
    await page.evaluate(() => {
      window.harness.services.deliveries.totals = window.originalTotals
    })
    await page.getByRole('button', { name: 'Keluar', exact: true }).click()
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await login('tetangga')
    await totals(0, 1)
    await page.evaluate(async () => {
      window.resolveOldTotals()
      await Promise.resolve()
      await Promise.resolve()
    })
    await totals(0, 1)
    assert.equal(await cards.count(), 1)
    await page.evaluate(() => window.harness.controls.expireSession())
    await pullRefresh(page, touch)
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    assert.equal(await page.locator('.delivery-summary').count(), 0)
    assert.deepEqual(errors, [])
    console.log(
      'PASS: whole-location totals across paging, local midnight rollover, separate package cards, compact status icons/reduced motion, detail keyboard access, responsive layout, totals error/retry, malformed totals, account switch/stale response, and expired session; no page errors.',
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
