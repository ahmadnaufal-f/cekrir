// Local browser verification tool; Playwright is supplied by the runner, not an app dependency.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fs = require('node:fs')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      deviceScaleFactor: 1,
    })
    const page = await context.newPage()
    await page.addInitScript(() => {
      window.__photoUrls = { created: [], revoked: [] }
      const make = URL.createObjectURL.bind(URL)
      const release = URL.revokeObjectURL.bind(URL)
      URL.createObjectURL = (b) => {
        const u = make(b)
        window.__photoUrls.created.push(u)
        return u
      }
      URL.revokeObjectURL = (u) => {
        window.__photoUrls.revoked.push(u)
        release(u)
      }
    })
    const errors = []
    page.on('pageerror', (e) => errors.push(e.message))
    const shots =
      require('node:path').resolve(__dirname, '../screenshots') + '/'
    async function capture(name) {
      await page.screenshot({ path: shots + name + '.png', fullPage: true })
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
        'horizontal overflow ' + name,
      )
    }
    async function login(id = 'admin@demo.test', password = 'demo1234') {
      await page.getByLabel('Identitas masuk', { exact: true }).fill(id)
      await page.getByLabel('Kata sandi', { exact: true }).fill(password)
      await page.getByRole('button', { name: 'Masuk', exact: true }).click()
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .waitFor()
    }
    async function route(value) {
      await page.evaluate((v) => (location.hash = v), value)
    }
    await page.goto('http://127.0.0.1:5173')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await page.keyboard.press('Tab')
    assert.equal(
      await page
        .locator('.skip-link')
        .evaluate((el) => el === document.activeElement),
      true,
      'keyboard skip link receives focus',
    )
    await page.keyboard.press('Tab')
    await capture('login-mobile')
    await login()
    await page.getByRole('button', { name: /DEMO-SPX-1001/ }).waitFor()
    await capture('admin-deliveries-mobile')
    await page.getByRole('button', { name: /DEMO-SPX-1001/ }).click()
    await page.locator('img').waitFor()
    await capture('delivery-complete-mobile')
    await route('/deliveries/delivery-demo-both-unavailable')
    await page.getByText('Foto tidak tersedia', { exact: true }).waitFor()
    await page
      .getByText('Detail pelacakan tidak tersedia', { exact: true })
      .waitFor()
    await capture('delivery-failures-mobile')
    assert.equal(
      await page.evaluate(() =>
        window.__photoUrls.created.every((u) =>
          window.__photoUrls.revoked.includes(u),
        ),
      ),
      true,
      'photo URLs released on detail navigation',
    )
    await route('/deliveries/delivery-demo-photo-unavailable')
    await page.getByText('Foto tidak tersedia', { exact: true }).waitFor()
    await page.getByText('Contoh status pelacakan', { exact: true }).waitFor()
    await capture('delivery-photo-unavailable-mobile')
    await route('/deliveries/delivery-demo-tracking-unavailable')
    await page
      .getByText('Detail pelacakan tidak tersedia', { exact: true })
      .waitFor()
    await page.locator('img').waitFor()
    await capture('delivery-tracking-unavailable-mobile')
    await route('/deliveries/delivery-demo-pending')
    await page.getByText('Memuat foto pengiriman…', { exact: true }).waitFor()
    await page
      .getByText('Sedang memeriksa detail pelacakan.', { exact: true })
      .waitFor()
    assert.equal(
      await page.getByText('Foto tidak tersedia', { exact: true }).count(),
      0,
    )
    await capture('delivery-pending-mobile')
    await route('/devices')
    await page
      .getByRole('heading', { name: 'Perangkat', exact: true })
      .waitFor()
    await capture('devices-mobile')
    await route('/members')
    await page
      .getByRole('heading', { name: 'Anggota', exact: true, level: 1 })
      .waitFor()
    await capture('members-mobile')
    await route('/setup')
    await page
      .getByRole('heading', { name: /Panduan/ })
      .first()
      .waitFor()
    await capture('setup-mobile')
    await route('/settings')
    await page
      .getByRole('heading', { name: 'Akun dan notifikasi', exact: true })
      .waitFor()
    await capture('settings-mobile')
    await page.getByRole('button', { name: 'Keluar', exact: true }).click()
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await login('anggota')
    await capture('member-deliveries-mobile')
    await route('/devices')
    await page.waitForTimeout(100)
    assert.equal(
      await page
        .getByRole('heading', { name: 'Perangkat', exact: true })
        .count(),
      0,
    )
    assert.equal(
      await page.getByRole('link', { name: 'Perangkat', exact: true }).count(),
      0,
    )
    await page.setViewportSize({ width: 1280, height: 900 })
    await capture('member-deliveries-desktop')
    await page.setViewportSize({ width: 320, height: 800 })
    await page.addStyleTag({ content: 'html{font-size:200%}' })
    await capture('member-deliveries-large-text')
    assert.deepEqual(errors, [])
    console.log(
      JSON.stringify(
        {
          status: 'passed',
          screenshots: fs.readdirSync(shots),
          pageErrors: errors,
        },
        null,
        2,
      ),
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
