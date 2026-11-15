// Local browser verification tool; Playwright is supplied by the runner, not an app dependency.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  try {
    const page = await browser.newPage({
      viewport: { width: 390, height: 844 },
    })
    const errors = []
    page.on('pageerror', (e) => errors.push(e.message))
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
    async function route(v) {
      await page.evaluate((v) => (location.hash = v), v)
    }
    async function login(id = 'admin@demo.test', pw = 'demo1234') {
      await page.getByLabel('Identitas masuk', { exact: true }).fill(id)
      await page.getByLabel('Kata sandi', { exact: true }).fill(pw)
      await page.getByRole('button', { name: 'Masuk', exact: true }).click()
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .waitFor()
    }
    await login()
    await route('/devices')
    await page.getByLabel('Nama perangkat', { exact: true }).fill('Scanner uji')
    await page
      .getByRole('button', { name: 'Daftarkan ESP32', exact: true })
      .click()
    await page
      .getByRole('heading', { name: 'Simpan kredensial perangkat' })
      .waitFor()
    assert.equal(
      await page
        .getByLabel('Identitas perangkat', { exact: true })
        .inputValue(),
      await page.evaluate(
        async () =>
          (await window.harness.services.devices.inventory()).esp32.id,
      ),
      'setup shows device identity, not its display name',
    )
    assert.equal(
      await page
        .getByLabel('Kredensial konfigurasi ESP32')
        .getAttribute('type'),
      'password',
    )
    await page
      .getByRole('button', { name: 'Selesai dan hapus kredensial' })
      .click()
    assert.equal(
      await page.getByLabel('Kredensial konfigurasi ESP32').count(),
      0,
    )
    await route('/deliveries')
    await page
      .getByRole('heading', { name: 'Paket diterima', exact: true })
      .waitFor()
    await page.evaluate(() => {
      const d = window.harness.services.devices,
        original = d.inventory
      let stale = true
      d.inventory = async () => {
        const r = await original()
        if (stale) {
          stale = false
          return { ...r, esp32: null }
        }
        return r
      }
    })
    await route('/devices')
    await page
      .getByLabel('Nama perangkat', { exact: true })
      .fill('Tidak boleh mengganti')
    await page
      .getByRole('button', { name: 'Daftarkan ESP32', exact: true })
      .click()
    await page
      .getByText(
        'Rumah tangga hanya dapat memiliki satu ESP32. Perangkat lama tetap tersimpan.',
        { exact: true },
      )
      .waitFor()
    await page.getByText('Scanner uji', { exact: true }).waitFor()
    const cameras = page.locator('.camera-card')
    await cameras
      .nth(0)
      .getByRole('button', { name: 'Jadikan kamera pengiriman' })
      .click()
    await cameras
      .nth(0)
      .getByText('Kamera pengiriman', { exact: true })
      .waitFor()
    await page.evaluate(() =>
      window.harness.controls.failNext('camera-selection'),
    )
    await cameras
      .nth(1)
      .getByRole('button', { name: 'Jadikan kamera pengiriman' })
      .click()
    await page
      .getByText(
        'Pilihan kamera belum berubah. Kamera pengiriman sebelumnya tetap digunakan; coba lagi.',
        { exact: true },
      )
      .waitFor()
    assert.equal(
      await cameras
        .nth(0)
        .getByText('Kamera pengiriman', { exact: true })
        .count(),
      1,
    )
    await page
      .getByLabel('Nama kamera', { exact: true })
      .fill('Kamera uji baru')
    await page
      .getByRole('button', { name: 'Tambahkan kamera', exact: true })
      .click()
    await page.getByRole('heading', { name: 'Kamera uji baru' }).waitFor()
    assert.equal(await cameras.count(), 3)
    await route('/members')
    await page.getByLabel('Nama tampilan', { exact: true }).fill('Anggota uji')
    await page.getByLabel('ID masuk', { exact: true }).fill('uji-anggota')
    await page
      .getByLabel('Kata sandi awal', { exact: true })
      .fill('uji-password-123')
    await page
      .getByRole('button', { name: 'Buat akun anggota', exact: true })
      .click()
    await page.getByRole('heading', { name: 'Akun anggota siap' }).waitFor()
    assert.equal(
      await page.evaluate(
        async () => (await window.harness.services.auth.restore()).role,
      ),
      'admin',
    )
    await page
      .getByRole('button', { name: 'Selesai dan hapus kata sandi' })
      .click()
    await page.getByText('Anggota uji', { exact: true }).waitFor()
    assert.equal(
      await page.getByLabel('Kata sandi awal', { exact: true }).inputValue(),
      '',
    )
    await route('/settings')
    await page
      .getByRole('button', { name: 'Aktifkan notifikasi', exact: true })
      .click()
    await page
      .getByRole('button', { name: 'Simulasikan kiriman diterima' })
      .click()
    assert.equal(await page.evaluate(() => location.hash), '#/settings')
    await page.getByRole('button', { name: 'Buka paket', exact: true }).click()
    await page.getByRole('heading', { name: 'Rincian pengiriman' }).waitFor()
    await page.getByText('DEMO-SPX-1001', { exact: true }).first().waitFor()
    await page.evaluate(() => window.harness.controls.expireSession())
    await route('/deliveries/delivery-demo-pending')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await page
      .getByLabel('Identitas masuk', { exact: true })
      .fill('admin@demo.test')
    await page.getByLabel('Kata sandi', { exact: true }).fill('demo1234')
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await page.getByRole('heading', { name: 'Rincian pengiriman' }).waitFor()
    assert.equal(
      await page.evaluate(() => location.hash),
      '#/deliveries/delivery-demo-pending',
    )
    await route('/settings')
    await page.getByRole('button', { name: 'Keluar', exact: true }).click()
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    await login('uji-anggota', 'uji-password-123')
    assert.equal(
      await page.getByRole('link', { name: 'Anggota', exact: true }).count(),
      0,
    )
    await route('/deliveries/delivery-tetangga-complete')
    await page
      .getByText('Anda tidak memiliki akses ke pengiriman ini.', {
        exact: true,
      })
      .waitFor()
    assert.equal(
      await page.getByText('DEMO-SPX-1001', { exact: true }).count(),
      0,
    )
    await route('/deliveries/missing-delivery')
    await page
      .getByText('Pengiriman ini tidak ditemukan atau sudah tidak tersedia.', {
        exact: true,
      })
      .waitFor()
    await page.evaluate(() => {
      window.harness.services.deliveries.photo = async () =>
        new Blob(['broken-image'], { type: 'image/jpeg' })
    })
    await route('/deliveries/delivery-demo-complete')
    await page.getByText('Foto tidak tersedia', { exact: true }).waitFor()
    await page.getByText('Contoh status pelacakan', { exact: true }).waitFor()
    await page.getByText('DEMO-SPX-1001', { exact: true }).first().waitFor()
    assert.deepEqual(errors, [])
    console.log(
      JSON.stringify(
        {
          status: 'passed',
          flows: [
            'ESP32 one-time credential cleanup',
            'stale second ESP32 409 preserves device',
            'camera selection failure preserves prior',
            'multiple cameras',
            'member creation preserves admin session',
            'member login',
            'foreground simulator does not navigate',
            'banner opens exact delivery',
            '401 login retains exact ID',
            'member route guard',
            'foreign household 403',
            'missing delivery 404',
            'image decode failure keeps tracking',
          ],
          pageErrors: errors,
        },
        null,
        2,
      ),
    )
  } finally {
    await browser.close()
  }
})().catch((e) => {
  console.error(e)
  process.exitCode = 1
})
