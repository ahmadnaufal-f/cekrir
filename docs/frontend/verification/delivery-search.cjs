// Actual Vue UI against explicit fixtures, including delayed/out-of-order searches.
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
      hasTouch: true,
      locale: 'id-ID',
    })
    const page = await context.newPage()
    const touch = await context.newCDPSession(page)
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.goto('http://127.0.0.1:5173')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    async function mount(account = 'admin@demo.test') {
      await page.evaluate(async (account) => {
        const source = await (await fetch('/src/App.vue')).text()
        const vuePath = source.match(/from ["']([^"']*vue\.js[^"']*)["']/)[1]
        const [{ createApp }, { default: App }, { createMockHarness }] =
          await Promise.all([
            import(vuePath),
            import('/src/App.vue'),
            import('/src/services/mock.ts'),
          ])
        document.querySelector('#app').__vue_app__.unmount()
        location.hash = '/deliveries'
        window.harness = createMockHarness({ pageSize: 3 })
        if (account === 'empty') {
          await window.harness.services.auth.signup({
            displayName: 'Pemilik Demo',
            email: 'empty@demo.test',
            householdName: 'Kantor Demo',
            password: 'demo-only-password',
          })
        } else {
          await window.harness.services.auth.login({
            loginId: account,
            password: 'demo1234',
          })
        }
        window.requests = []
        window.held = []
        window.holdSearch = null
        const list = window.harness.services.deliveries.list
        window.harness.services.deliveries.list = async (cursor, query) => {
          window.requests.push({ cursor, search: query?.search })
          const result = await list(cursor, query)
          if (query?.search === window.holdSearch) {
            return new Promise((resolve) =>
              window.held.push(() => resolve(result)),
            )
          }
          return result
        }
        createApp(App, { services: window.harness.services }).mount('#app')
      }, account)
      await page.waitForFunction(
        () =>
          document
            .querySelector('#delivery-results')
            ?.getAttribute('aria-busy') === 'false',
      )
      await page.waitForFunction(
        () =>
          document
            .querySelector('.delivery-summary')
            ?.getAttribute('aria-busy') === 'false',
      )
    }
    const search = page.getByRole('searchbox', {
      name: 'Cari paket',
      exact: true,
    })
    const cards = page.locator('.delivery-card')
    async function countCards(count) {
      await page.waitForFunction(
        (count) =>
          document.querySelectorAll('.delivery-card').length === count &&
          document
            .querySelector('#delivery-results')
            ?.getAttribute('aria-busy') === 'false',
        count,
      )
    }
    async function capture(name) {
      const viewport = page.viewportSize()
      await page.setViewportSize({ width: viewport.width, height: 1000 })
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.evaluate(() => document.activeElement?.blur())
      await page.screenshot({
        path: path.resolve(__dirname, '../screenshots/' + name + '.png'),
        fullPage: false,
        animations: 'disabled',
      })
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
        name + ' must fit the viewport',
      )
      await page.setViewportSize(viewport)
    }
    await mount()
    await countCards(3)
    assert.equal(await search.count(), 1)
    assert.equal(await search.getAttribute('aria-controls'), 'delivery-results')
    const subtitle = page.locator('.deliveries-screen__header p')
    assert.match(
      await subtitle.innerText(),
      /lokasi penerimaan ini\.\s+Tarik ke bawah untuk memperbarui\./,
    )
    assert.equal(
      await page
        .locator('.pull-to-refresh')
        .getByText('Tarik ke bawah untuk memperbarui.', { exact: true })
        .count(),
      0,
    )
    assert.equal(await page.locator('.deliveries-panel__pull-hint').count(), 0)
    assert.equal(
      await page.locator('.pull-to-refresh .deliveries-screen__header').count(),
      0,
    )

    // A resi on the third page is searchable from the first page.
    await search.fill('1009')
    await countCards(1)
    assert.match(await cards.first().innerText(), /DEMO-SPX-1009/)
    assert.match(
      await page.locator('.delivery-summary__all-time').innerText(),
      /9/,
    )
    await capture('package-search-mobile')
    await pullRefresh(page, touch)
    await countCards(1)
    assert.equal(await search.inputValue(), '1009')
    assert.match(await cards.first().innerText(), /1009/)

    await search.fill('  sPx  ')
    await countCards(3)
    const more = page.getByRole('button', {
      name: 'Muat pengiriman berikutnya',
      exact: true,
    })
    await more.click()
    await countCards(6)
    assert.equal(
      await page.evaluate(() => window.requests.at(-1).search),
      'sPx',
    )
    assert.ok(await page.evaluate(() => Boolean(window.requests.at(-1).cursor)))

    await search.fill('no-such-package.*')
    await page
      .getByRole('heading', { name: 'Tidak ada paket yang cocok', exact: true })
      .waitFor()
    assert.equal(await cards.count(), 0)
    assert.equal(
      await search.count(),
      1,
      'search stays available with no matches',
    )
    assert.equal(await more.count(), 0, 'old pagination is cleared')
    await capture('package-no-results-mobile')
    await page
      .getByRole('button', { name: 'Hapus pencarian', exact: true })
      .focus()
    await page.keyboard.press('Enter')
    assert.equal(await search.inputValue(), '')
    assert.equal(
      await search.evaluate((el) => el === document.activeElement),
      true,
    )
    await countCards(3)

    // Search starts a new request generation before the debounce timer fires.
    await page.evaluate(() => {
      window.holdSearch = '1001'
    })
    await search.fill('1001')
    await page.waitForFunction(() => window.held.length === 1)
    assert.equal(
      await page.locator('.empty-state-card').count(),
      0,
      'pending results use skeletons',
    )
    await search.fill('1009')
    await countCards(1)
    await page.evaluate(() => window.held[0]())
    await page.waitForTimeout(100)
    assert.match(
      await cards.first().innerText(),
      /1009/,
      'an obsolete search cannot replace the latest result',
    )
    await page.evaluate(() => {
      window.holdSearch = null
    })
    await search.fill('100')
    await search.fill('1002')
    await search.fill('1003')
    await countCards(1)
    assert.match(await cards.first().innerText(), /1003/)

    await page.setViewportSize({ width: 320, height: 900 })
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
    await search.fill('not-found')
    await page
      .getByRole('heading', { name: 'Tidak ada paket yang cocok', exact: true })
      .waitFor()
    await capture('package-search-large-text')
    await page.reload()
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await page.setViewportSize({ width: 390, height: 844 })
    await mount('tetangga')
    await countCards(1)
    assert.equal(await search.count(), 0, 'a single delivery needs no search')
    await mount('empty')
    await page
      .getByRole('heading', { name: 'Belum ada pengiriman', exact: true })
      .waitFor()
    assert.equal(await search.count(), 0)
    assert.equal(await cards.count(), 0)
    assert.match(
      await page.locator('.delivery-summary__all-time').innerText(),
      /0/,
    )
    await capture('package-empty-mobile')

    const desktop = await browser.newPage({
      viewport: { width: 1280, height: 900 },
    })
    await desktop.goto('http://127.0.0.1:5173')
    await desktop
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await desktop.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await desktop.getByRole('button', { name: 'Masuk', exact: true }).click()
    await desktop.locator('.delivery-card').first().waitFor()
    assert.equal(
      await desktop
        .locator('.deliveries-screen__touch-instruction')
        .isVisible(),
      false,
    )
    assert.equal(
      await desktop.getByRole('searchbox', { name: 'Cari paket' }).count(),
      1,
    )
    assert.deepEqual(errors, [])
    console.log(
      'PASS: combined subtitle, reusable empty state, conditional search, all-page resi/courier filtering, pagination, literal no-match, keyboard clear/focus, latest-request guards, filtered pull refresh, global totals, single/empty scope, desktop and 320px/200% text.',
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
