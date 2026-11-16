// Real Chromium touch input through CDP against explicit development fixtures.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const path = require('node:path')
const { touchDrag, pullRefresh } = require('./touch.cjs')

;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true,
    })
    const page = await context.newPage()
    const touch = await context.newCDPSession(page)
    const errors = []
    let documentLoads = 0
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('request', (request) => {
      if (
        request.isNavigationRequest() &&
        request.resourceType() === 'document'
      )
        documentLoads++
    })
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
      window.harness = createMockHarness()
      createApp(App, { services: window.harness.services }).mount('#app')
    })
    await page
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await page.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await page.locator('.delivery-card').first().waitFor()
    await page.waitForFunction(
      () =>
        document
          .querySelector('.pull-to-refresh__content')
          ?.getAttribute('aria-busy') === 'false',
    )
    assert.equal(
      await page
        .getByRole('button', { name: 'Muat ulang', exact: true })
        .count(),
      0,
    )
    await page.evaluate(() => {
      window.calls = { list: 0, totals: 0 }
      window.originalList = window.harness.services.deliveries.list
      window.originalTotals = window.harness.services.deliveries.totals
      window.harness.services.deliveries.list = async (...args) => {
        window.calls.list++
        return window.originalList(...args)
      }
      window.harness.services.deliveries.totals = async (query) => {
        window.calls.totals++
        return window.originalTotals(query)
      }
    })
    async function atTop() {
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.waitForFunction(() => window.scrollY === 0)
      const box = await page.locator('.pull-to-refresh').boundingBox()
      return { x: box.x + 90, y: box.y + 18 }
    }
    async function noRefresh() {
      assert.deepEqual(await page.evaluate(() => window.calls), {
        list: 0,
        totals: 0,
      })
    }
    const initialDocumentLoads = documentLoads
    assert.equal(
      await page.locator('.pull-to-refresh .deliveries-screen__header').count(),
      0,
    )
    const title = page.getByRole('heading', {
      name: 'Paket diterima',
      exact: true,
    })
    const subtitle = page.locator('.deliveries-screen__header p')
    const titleBefore = await title.boundingBox()
    const subtitleBefore = await subtitle.boundingBox()
    await touchDrag(page, touch, {
      x: titleBefore.x + 80,
      y: titleBefore.y + 16,
      dy: 160,
    })
    await noRefresh()
    await touchDrag(page, touch, { ...(await atTop()), dy: 60 })
    await noRefresh()
    await touchDrag(page, touch, { ...(await atTop()), dx: 100, dy: 10 })
    await noRefresh()
    await touchDrag(page, touch, { ...(await atTop()), dy: -120 })
    await page.waitForFunction(() => window.scrollY > 0)
    await noRefresh()
    await page.evaluate(() => window.scrollTo(0, 300))
    const card = await page.locator('.delivery-card').first().boundingBox()
    await touchDrag(page, touch, { x: card.x + 80, y: card.y + 20, dy: 120 })
    await noRefresh()
    await touchDrag(page, touch, { ...(await atTop()), dy: 160, cancel: true })
    await noRefresh()
    const origin = await atTop()
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchStart',
      touchPoints: [{ ...origin, id: 1 }],
    })
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ x: origin.x, y: origin.y + 40, id: 1 }],
    })
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchStart',
      touchPoints: [
        { x: origin.x, y: origin.y + 40, id: 1 },
        { x: 10, y: origin.y + 40, id: 2 },
      ],
    })
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchEnd',
      touchPoints: [],
    })
    await noRefresh()
    await page.evaluate(() => {
      window.harness.services.deliveries.list = async (...args) => {
        window.calls.list++
        const result = await window.originalList(...args)
        return new Promise((resolve) => {
          window.resolveList = () => resolve(result)
        })
      }
      window.harness.services.deliveries.totals = async (query) => {
        window.calls.totals++
        const result = await window.originalTotals(query)
        return new Promise((resolve) => {
          window.resolveTotals = () => resolve(result)
        })
      }
    })
    const fullPull = await atTop()
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchStart',
      touchPoints: [{ ...fullPull, id: 1 }],
    })
    for (let step = 1; step <= 8; step++) {
      await touch.send('Input.dispatchTouchEvent', {
        type: 'touchMove',
        touchPoints: [{ x: fullPull.x, y: fullPull.y + step * 20, id: 1 }],
      })
      await page.waitForTimeout(20)
    }
    await page
      .locator('.pull-to-refresh__indicator')
      .getByText('Lepaskan untuk memperbarui', { exact: true })
      .waitFor()
    assert.ok(
      Math.abs((await title.boundingBox()).y - titleBefore.y) < 1,
      'title stays outside the moving pull content',
    )
    assert.ok(
      Math.abs((await subtitle.boundingBox()).y - subtitleBefore.y) < 1,
      'subtitle stays outside the moving pull content',
    )
    await noRefresh()
    await touch.send('Input.dispatchTouchEvent', {
      type: 'touchEnd',
      touchPoints: [],
    })
    await page.waitForFunction(
      () => window.calls.list === 1 && window.calls.totals === 1,
    )
    await page.getByText('Memperbarui paket…', { exact: true }).waitFor()
    assert.equal(
      await page
        .getByText('Memperbarui daftar pengiriman…', { exact: true })
        .count(),
      0,
    )
    assert.equal(
      await page.getByText('Memuat ringkasan…', { exact: true }).count(),
      0,
    )
    assert.equal(
      await page.getByRole('status').filter({ hasText: 'Memperbarui' }).count(),
      1,
    )
    assert.equal(
      await page.locator('.delivery-summary__value-skeleton').count(),
      2,
    )
    assert.equal(await page.locator('.delivery-card-skeleton').count(), 9)
    assert.equal(await page.locator('.delivery-card').count(), 0)
    await page.screenshot({
      path: path.resolve(
        __dirname,
        '../screenshots/pull-refresh-loading-mobile.png',
      ),
      fullPage: false,
      animations: 'disabled',
    })
    await page.setViewportSize({ width: 320, height: 800 })
    const largeText = await page.addStyleTag({
      content: 'html{font-size:200%}',
    })
    await page.waitForFunction(() => {
      const indicator = document
        .querySelector('.pull-to-refresh__indicator')
        .getBoundingClientRect()
      const summary = document
        .querySelector('.delivery-summary')
        .getBoundingClientRect()
      return summary.top >= indicator.bottom - 1
    })
    const indicator = await page
      .locator('.pull-to-refresh__indicator')
      .boundingBox()
    const summary = await page.locator('.delivery-summary').boundingBox()
    assert.ok(
      summary.y >= indicator.y + indicator.height - 1,
      'loading feedback clears enlarged summary content',
    )
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    )
    await page.screenshot({
      path: path.resolve(
        __dirname,
        '../screenshots/pull-refresh-loading-large-text.png',
      ),
      fullPage: false,
      animations: 'disabled',
    })
    await largeText.evaluate((el) => el.remove())
    await page.setViewportSize({ width: 390, height: 844 })
    await touchDrag(page, touch, { ...fullPull, dy: 160 })
    assert.deepEqual(
      await page.evaluate(() => window.calls),
      { list: 1, totals: 1 },
      'no duplicate refresh while requests are in flight',
    )
    await page.evaluate(() => {
      window.oldList = window.resolveList
      window.oldTotals = window.resolveTotals
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await page.waitForFunction(
      () => window.calls.list === 2 && window.calls.totals === 2,
    )
    await page.evaluate(() => {
      window.oldList()
      window.oldTotals()
    })
    await page.getByText('Memperbarui paket…', { exact: true }).waitFor()
    await page.evaluate(() => window.resolveList())
    await page.getByText('Memperbarui paket…', { exact: true }).waitFor()
    assert.equal(
      await page.locator('.pull-to-refresh__content').getAttribute('aria-busy'),
      'true',
      'indicator waits for totals as well as list',
    )
    await page.evaluate(() => window.resolveTotals())
    await page.waitForFunction(
      () =>
        document
          .querySelector('.pull-to-refresh__content')
          .getAttribute('aria-busy') === 'false',
    )
    assert.equal(
      await page
        .locator('.pull-to-refresh__indicator')
        .getAttribute('aria-hidden'),
      'true',
    )
    assert.equal(
      documentLoads,
      initialDocumentLoads,
      'pull refresh does not reload the browser document',
    )
    await page.evaluate(() => {
      window.harness.services.deliveries.list = window.originalList
      window.harness.services.deliveries.totals = window.originalTotals
    })
    await page.evaluate(() => window.scrollTo(0, 0))
    const firstCard = await page.locator('.delivery-card').first().boundingBox()
    await touchDrag(page, touch, {
      x: firstCard.x + 100,
      y: firstCard.y + 20,
      dy: 40,
    })
    assert.equal(
      await page.evaluate(() => location.hash),
      '#/deliveries',
      'a short drag on a card does not open it',
    )
    const tap = await page.locator('.delivery-card').first().boundingBox()
    await page.touchscreen.tap(tap.x + 100, tap.y + 20)
    await page
      .getByRole('heading', { name: 'Rincian pengiriman', exact: true })
      .waitFor()
    await page
      .getByRole('button', { name: 'Kembali ke daftar', exact: true })
      .click()
    await page.waitForFunction(
      () =>
        document
          .querySelector('.pull-to-refresh__content')
          ?.getAttribute('aria-busy') === 'false',
    )
    await page.evaluate(() => {
      window.harness.services.deliveries.list = async () => {
        throw new Error('mock list failure')
      }
      window.harness.services.deliveries.totals = async () => {
        throw new Error('mock totals failure')
      }
    })
    await pullRefresh(page, touch)
    await page
      .getByText('Ringkasan paket belum dapat dimuat.', { exact: true })
      .waitFor()
    await page
      .getByText(
        'Daftar pengiriman tidak dapat dimuat. Periksa koneksi lalu coba lagi.',
        { exact: true },
      )
      .waitFor()
    await page.waitForFunction(
      () =>
        document
          .querySelector('.pull-to-refresh__content')
          .getAttribute('aria-busy') === 'false',
    )
    assert.equal(
      await page
        .locator('.pull-to-refresh__indicator')
        .getAttribute('aria-hidden'),
      'true',
    )
    assert.equal(documentLoads, initialDocumentLoads)
    const desktop = await browser.newContext({
      viewport: { width: 1280, height: 900 },
    })
    const desktopPage = await desktop.newPage()
    await desktopPage.goto('http://127.0.0.1:5173')
    await desktopPage
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await desktopPage.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await desktopPage
      .getByRole('button', { name: 'Masuk', exact: true })
      .click()
    await desktopPage.locator('.delivery-card').first().waitFor()
    assert.equal(
      await desktopPage
        .getByRole('button', { name: 'Muat ulang', exact: true })
        .count(),
      0,
    )
    assert.equal(
      await desktopPage.locator('.deliveries-panel__pull-hint').isVisible(),
      false,
    )
    await desktopPage.reload()
    await desktopPage
      .getByRole('heading', { name: 'Masuk', exact: true })
      .waitFor()
    assert.deepEqual(errors, [])
    console.log(
      'PASS: Chromium CDP touch verifies short/horizontal/upward/canceled/multi-touch gestures, native scrolling away from the top, release threshold, single combined list/totals refresh, completion indicator, no browser reload or accidental card navigation, normal taps, error recovery, and desktop browser reload. No physical-device or WebKit evidence claimed.',
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
