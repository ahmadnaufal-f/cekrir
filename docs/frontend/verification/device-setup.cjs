// Local browser verification for device tabs, registration, and setup guides.
// Playwright and Chromium are supplied by the verification runner.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const path = require('node:path')
const { touchDrag } = require('./touch.cjs')

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
      timezoneId: 'UTC',
    })
    const page = await context.newPage()
    const touch = await context.newCDPSession(page)
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
      window.harness = createMockHarness()
      createApp(App, { services: window.harness.services }).mount('#app')
    })

    async function route(value) {
      await page.evaluate((next) => (location.hash = next), value)
    }
    async function login(id = 'admin@demo.test', password = 'demo1234') {
      await page.getByLabel('Identitas masuk', { exact: true }).fill(id)
      await page.getByLabel('Kata sandi', { exact: true }).fill(password)
      await page.getByRole('button', { name: 'Masuk', exact: true }).click()
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .waitFor()
    }
    async function createEmptyAdmin() {
      await page
        .getByRole('button', {
          name: 'Buat lokasi dan akun admin',
          exact: true,
        })
        .click()
      await page
        .getByLabel('Nama Anda', { exact: true })
        .fill('Admin Perangkat')
      await page
        .getByLabel('Email', { exact: true })
        .fill('device-setup@demo.test')
      await page
        .getByLabel('Nama lokasi penerimaan', { exact: true })
        .fill('Lokasi Uji Perangkat')
      await page
        .getByLabel('Kata sandi', { exact: true })
        .fill('device-demo1234')
      await page
        .getByRole('button', {
          name: 'Buat lokasi dan akun admin',
          exact: true,
        })
        .click()
      await page
        .getByRole('heading', { name: 'Paket diterima', exact: true })
        .waitFor()
    }
    async function waitForDeviceState(category, state) {
      await page.locator(`#device-tabs-${category}`).waitFor()
      await page
        .locator(`#device-tabs-${category} .tab-selector__status--${state}`)
        .waitFor()
    }
    async function assertNoPageOverflow(label) {
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        ),
        false,
        label + ' must not create page-level horizontal overflow',
      )
    }
    async function capture(name) {
      const viewport = page.viewportSize()
      await page.setViewportSize({ width: viewport.width, height: 1000 })
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.evaluate(() => document.activeElement?.blur())
      await page.mouse.move(0, 0)
      await page.screenshot({
        path: path.resolve(__dirname, '../screenshots/' + name + '.png'),
        fullPage: false,
        animations: 'disabled',
      })
      await assertNoPageOverflow(name)
      await page.setViewportSize(viewport)
    }
    async function assertGuideSlides(kind, expectedCount) {
      const carousel = page.locator('.setup-step-carousel')
      await carousel.waitFor()
      const slides = page.locator('.setup-step')
      const activeStep = page.locator('.setup-step[aria-hidden="false"]')
      const progress = page.locator('.setup-step-carousel__meter')
      const viewport = page.locator('.setup-step-carousel__viewport')
      async function waitForIndex(index) {
        await page.waitForFunction((activeIndex) => {
          const element = document.querySelector(
            '.setup-step-carousel__viewport',
          )
          const meter = document.querySelector('.setup-step-carousel__meter')
          return (
            element &&
            Math.abs(element.scrollLeft - element.clientWidth * activeIndex) <
              2 &&
            meter?.getAttribute('aria-valuenow') === String(activeIndex + 1)
          )
        }, index)
      }
      assert.equal(await slides.count(), expectedCount)
      const alts = []
      for (let index = 0; index < expectedCount; index++) {
        const slide = slides.nth(index)
        const image = slide.locator('img')
        assert.equal(
          await image.count(),
          1,
          kind + ' slide has one illustration',
        )
        assert.equal(
          await slide.locator('p').count(),
          1,
          kind + ' slide has one paragraph',
        )
        const alt = await image.getAttribute('alt')
        assert.ok(
          alt?.trim(),
          kind + ' illustrations have descriptive alt text',
        )
        alts.push(alt)
        await image.evaluate(async (element) => {
          if (!element.complete) {
            await new Promise((resolve, reject) => {
              element.addEventListener('load', resolve, { once: true })
              element.addEventListener('error', reject, { once: true })
            })
          }
          if (element.decode) await element.decode()
        })
        assert.ok(
          await image.evaluate(
            (element) => element.complete && element.naturalWidth > 0,
          ),
          kind + ' illustration ' + (index + 1) + ' is loaded',
        )
      }
      assert.equal(
        new Set(alts).size,
        expectedCount,
        kind + ' illustration alt text is unique',
      )
      const previous = page.getByRole('button', {
        name: 'Sebelumnya',
        exact: true,
      })
      const next = page.getByRole('button', { name: 'Berikutnya', exact: true })
      await previous.waitFor()
      await next.waitFor()
      assert.equal(
        await previous.isDisabled(),
        true,
        kind + ' starts at its first step',
      )
      assert.equal(await next.isDisabled(), false, kind + ' can advance')
      assert.equal(
        await page.locator('.setup-step-carousel__progress').innerText(),
        `Langkah 1 dari ${expectedCount}`,
      )

      const firstContent = await activeStep.innerText()
      assert.equal(await progress.getAttribute('aria-valuenow'), '1')
      await next.click()
      await waitForIndex(1)
      await page.waitForFunction(
        (previousContent) =>
          document.querySelector('.setup-step[aria-hidden="false"]')
            ?.innerText !== previousContent,
        firstContent,
      )
      const secondContent = await activeStep.innerText()
      assert.notEqual(
        secondContent,
        firstContent,
        kind + ' advances exactly one visible step',
      )
      assert.equal(await progress.getAttribute('aria-valuenow'), '2')
      await page.waitForTimeout(1100)
      assert.equal(
        await activeStep.innerText(),
        secondContent,
        kind + ' does not auto-advance',
      )
      await previous.click()
      await waitForIndex(0)
      await page.waitForFunction(
        (first) =>
          document.querySelector('.setup-step[aria-hidden="false"]')
            ?.innerText === first,
        firstContent,
      )

      // Keyboard input should operate the carousel, including its end keys.
      await viewport.focus()
      await page.keyboard.press('ArrowRight')
      await waitForIndex(1)
      await page.waitForFunction(
        (second) =>
          document.querySelector('.setup-step[aria-hidden="false"]')
            ?.innerText === second,
        secondContent,
      )
      await page.keyboard.press('End')
      await waitForIndex(expectedCount - 1)
      await page.waitForFunction(() => {
        const meter = document.querySelector('.setup-step-carousel__meter')
        return (
          meter?.getAttribute('aria-valuenow') ===
          meter?.getAttribute('aria-valuemax')
        )
      })
      assert.equal(
        await next.isDisabled(),
        true,
        kind + ' End key reaches the final step',
      )
      await page.keyboard.press('Home')
      await waitForIndex(0)
      await page.waitForFunction(
        (first) =>
          document.querySelector('.setup-step[aria-hidden="false"]')
            ?.innerText === first,
        firstContent,
      )
      assert.equal(
        await previous.isDisabled(),
        true,
        kind + ' Home key returns to the first step',
      )

      // Synthesize a native Chromium touch swipe on the actual carousel.
      await viewport.scrollIntoViewIfNeeded()
      await waitForIndex(0)
      const box = await viewport.boundingBox()
      assert.ok(box && box.width > 100, kind + ' carousel has a swipe surface')
      await touchDrag(page, touch, {
        x: box.x + box.width * 0.8,
        y: box.y + box.height * 0.5,
        dx: -Math.min(220, box.width * 0.55),
        dy: 0,
      })
      await waitForIndex(1)
      await page.waitForFunction(
        (second) =>
          document.querySelector('.setup-step[aria-hidden="false"]')
            ?.innerText === second,
        secondContent,
      )
      await assertNoPageOverflow(kind + ' guide carousel')
      await viewport.focus()
      await page.keyboard.press('Home')
      await waitForIndex(0)
      return { carousel, slides, expectedCount }
    }

    // Unauthenticated direct links to either new guide are guarded.
    await route('/devices/setup/esp32')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    assert.equal(await page.locator('.setup-step-carousel').count(), 0)
    assert.equal(await page.evaluate(() => location.hash), '#/login')

    await createEmptyAdmin()
    await route('/devices')
    await waitForDeviceState('esp32', 'incomplete')
    await waitForDeviceState('bardi', 'incomplete')
    const espTab = page.getByRole('tab', { name: /^ESP32/ })
    const cameraTab = page.getByRole('tab', { name: /^Kamera/ })
    const espPanel = page.locator('#device-panel-esp32')
    const cameraPanel = page.locator('#device-panel-bardi')
    assert.equal(
      await espTab.getAttribute('aria-controls'),
      'device-panel-esp32',
    )
    assert.equal(
      await cameraTab.getAttribute('aria-controls'),
      'device-panel-bardi',
    )
    assert.equal(await espTab.getAttribute('aria-selected'), 'true')
    assert.equal(await espPanel.isVisible(), true)
    assert.equal(await cameraPanel.isVisible(), false)
    assert.equal(
      await page.locator('.device-guide, .setup-step-carousel').count(),
      0,
    )
    assert.equal(await page.locator('.devices-screen form').count(), 0)
    const espGuideLink = page.getByRole('link', {
      name: 'Lihat panduan ESP32',
      exact: true,
    })
    const espRegister = page.getByRole('button', {
      name: 'Daftarkan perangkat',
      exact: true,
    })
    await espGuideLink.waitFor()
    await espRegister.waitFor()
    assert.equal(
      await espGuideLink.evaluate(
        (guide, opener) =>
          Boolean(
            guide.compareDocumentPosition(opener) &
            Node.DOCUMENT_POSITION_FOLLOWING,
          ),
        await espRegister.elementHandle(),
      ),
      true,
      'the guide link appears before the registration opener',
    )
    await capture('devices-tabs-mobile')

    // Tab arrows, Home, and End move focus and selection with linked panels.
    await espTab.focus()
    await page.keyboard.press('ArrowRight')
    await page.waitForFunction(
      () =>
        document
          .querySelector('#device-tabs-bardi')
          ?.getAttribute('aria-selected') === 'true',
    )
    assert.equal(
      await cameraTab.evaluate((element) => element === document.activeElement),
      true,
    )
    assert.equal(await cameraPanel.isVisible(), true)
    assert.equal(await espPanel.isVisible(), false)
    await page.keyboard.press('Home')
    await page.waitForFunction(
      () =>
        document
          .querySelector('#device-tabs-esp32')
          ?.getAttribute('aria-selected') === 'true',
    )
    assert.equal(
      await espTab.evaluate((element) => element === document.activeElement),
      true,
    )
    await page.keyboard.press('End')
    await page.waitForFunction(
      () =>
        document
          .querySelector('#device-tabs-bardi')
          ?.getAttribute('aria-selected') === 'true',
    )
    assert.equal(
      await cameraTab.evaluate((element) => element === document.activeElement),
      true,
    )
    await cameraTab.click()
    await page.waitForFunction(
      () =>
        document
          .querySelector('#device-tabs-bardi')
          ?.getAttribute('aria-selected') === 'true',
    )
    await page
      .getByText('Belum ada kamera BARDI yang terdaftar.', { exact: true })
      .waitFor()
    assert.equal(
      await page
        .locator('#device-tabs-bardi .tab-selector__status--incomplete')
        .count(),
      1,
    )
    assert.equal(
      await page
        .getByRole('link', { name: 'Lihat panduan kamera', exact: true })
        .count(),
      1,
    )
    await capture('devices-camera-tab-mobile')

    // The separate camera guide has accessible, loaded, one-image steps and no registration form.
    await page
      .getByRole('link', { name: 'Lihat panduan kamera', exact: true })
      .click()
    await page.locator('.setup-step-carousel').waitFor()
    assert.equal(
      await page.evaluate(() => location.hash),
      '#/devices/setup/cameras',
    )
    assert.equal(await page.locator('.devices-screen').count(), 0)
    assert.equal(await page.locator('form').count(), 0)
    await assertGuideSlides('camera', 3)
    await capture('device-guide-camera-mobile')
    await assertNoPageOverflow('camera guide mobile')

    // The guide CTA returns to the right tab and opens the native modal.
    await page
      .getByRole('button', { name: 'Daftarkan perangkat', exact: true })
      .click()
    const dialog = page.getByRole('dialog')
    await dialog.waitFor()
    assert.equal(await page.evaluate(() => location.hash), '#/devices')
    assert.equal(
      await page.locator('#device-tabs-bardi').getAttribute('aria-selected'),
      'true',
    )
    assert.equal(
      await dialog.evaluate(
        (element) => element instanceof HTMLDialogElement && element.open,
      ),
      true,
    )
    assert.equal(
      await dialog.getByLabel('Nama kamera', { exact: true }).count(),
      1,
    )
    assert.equal(
      await dialog
        .getByLabel('Kata sandi kamera', { exact: true })
        .inputValue(),
      '',
    )
    await capture('device-registration-camera-mobile')
    // Native showModal must keep keyboard focus in the dialog, above the fixed nav.
    for (let index = 0; index < 6; index++) {
      await page.keyboard.press('Tab')
      assert.equal(
        await dialog.evaluate((element) =>
          element.contains(document.activeElement),
        ),
        true,
        'camera modal traps focus within its content',
      )
      assert.notEqual(
        await page.evaluate(
          () => document.activeElement?.closest('#main-navigation') !== null,
        ),
        true,
        'modal focus cannot move behind the fixed navigation',
      )
    }
    await page.getByRole('button', { name: 'Tutup', exact: true }).click()
    await dialog.waitFor({ state: 'hidden' })
    const cameraRegister = page.getByRole('button', {
      name: 'Daftarkan perangkat',
      exact: true,
    })
    await cameraRegister.click()
    await dialog.waitFor()
    await page.keyboard.press('Escape')
    await dialog.waitFor({ state: 'hidden' })
    assert.equal(
      await cameraRegister.evaluate(
        (element) => element === document.activeElement,
      ),
      true,
      'Escape restores focus to the camera registration opener',
    )

    // A close/reopen clears nonsecret draft fields.
    await cameraRegister.click()
    const cameraName = page.getByLabel('Nama kamera', { exact: true })
    await cameraName.fill('Draf sementara')
    await page.getByRole('button', { name: 'Tutup', exact: true }).click()
    await cameraRegister.click()
    assert.equal(
      await page.getByLabel('Nama kamera', { exact: true }).inputValue(),
      '',
    )
    await page
      .getByLabel('Nama kamera', { exact: true })
      .fill('Kamera Uji Terkonfigurasi')
    await page.locator('details summary').click()
    await page
      .getByLabel('Alamat RTSP', { exact: true })
      .fill('rtsp://camera.invalid/stream')
    await page
      .getByLabel('Nama pengguna', { exact: true })
      .fill('operator-demo')
    await page
      .getByLabel('Kata sandi kamera', { exact: true })
      .fill('camera-demo-secret')
    await page.evaluate(() =>
      window.harness.controls.failNext('camera-registration'),
    )
    await page
      .getByRole('button', { name: 'Tambahkan kamera', exact: true })
      .click()
    await page
      .getByRole('alert')
      .filter({ hasText: 'Kamera belum dapat disimpan.' })
      .waitFor()
    assert.equal(
      await page.getByLabel('Nama kamera', { exact: true }).inputValue(),
      'Kamera Uji Terkonfigurasi',
    )
    assert.equal(
      await page.getByLabel('Alamat RTSP', { exact: true }).inputValue(),
      'rtsp://camera.invalid/stream',
    )
    assert.equal(
      await page.getByLabel('Nama pengguna', { exact: true }).inputValue(),
      'operator-demo',
    )
    assert.equal(
      await page.getByLabel('Kata sandi kamera', { exact: true }).inputValue(),
      '',
    )
    assert.equal(
      await page.locator('.camera-card').count(),
      0,
      'failed registration does not add a camera',
    )
    await page.getByRole('button', { name: 'Tutup', exact: true }).click()

    // A pending save disables duplicate submission and marks the form busy.
    await cameraRegister.click()
    await page
      .getByLabel('Nama kamera', { exact: true })
      .fill('Kamera Uji Terkonfigurasi')
    await page.locator('details summary').click()
    await page
      .getByLabel('Alamat RTSP', { exact: true })
      .fill('rtsp://camera.invalid/stream')
    await page
      .getByLabel('Nama pengguna', { exact: true })
      .fill('operator-demo')
    await page
      .getByLabel('Kata sandi kamera', { exact: true })
      .fill('camera-demo-secret')
    await page.evaluate(() => {
      window.originalRegisterCamera =
        window.harness.services.devices.registerCamera
      window.cameraRegistrationCalls = 0
      window.releaseCameraRegistration = null
      window.harness.services.devices.registerCamera = async (...args) => {
        window.cameraRegistrationCalls++
        await new Promise(
          (resolve) => (window.releaseCameraRegistration = resolve),
        )
        return window.originalRegisterCamera(...args)
      }
    })
    await page
      .getByRole('button', { name: 'Tambahkan kamera', exact: true })
      .click()
    const cameraForm = dialog.locator('form')
    await page.waitForFunction(() => window.cameraRegistrationCalls === 1)
    assert.equal(await cameraForm.getAttribute('aria-busy'), 'true')
    assert.equal(
      await cameraForm
        .getByRole('button', { name: 'Menyimpan kamera…', exact: true })
        .isDisabled(),
      true,
    )
    await cameraForm.evaluate((form) => form.requestSubmit())
    await page.waitForTimeout(50)
    assert.equal(await page.evaluate(() => window.cameraRegistrationCalls), 1)
    await page.evaluate(() => window.releaseCameraRegistration())
    await page
      .getByRole('heading', { name: 'Kamera Uji Terkonfigurasi', exact: true })
      .waitFor()
    await dialog.waitFor({ state: 'hidden' })
    await page.evaluate(() => {
      window.harness.services.devices.registerCamera =
        window.originalRegisterCamera
    })
    await page
      .getByText('Konfigurasi tersimpan · koneksi belum diverifikasi', {
        exact: true,
      })
      .waitFor()
    await page.getByText('Belum diuji', { exact: true }).waitFor()
    assert.equal(
      await page.locator('.camera-card').count(),
      1,
      'camera registration saves the first camera',
    )
    assert.equal(
      await page
        .getByRole('link', { name: 'Lihat panduan kamera', exact: true })
        .count(),
      1,
    )
    const configuredCamera = page.locator('.camera-card').filter({
      has: page.getByRole('heading', {
        name: 'Kamera Uji Terkonfigurasi',
        exact: true,
      }),
    })
    await configuredCamera
      .getByRole('button', { name: 'Jadikan kamera pengiriman', exact: true })
      .click()
    await configuredCamera
      .getByText('Kamera pengiriman', { exact: true })
      .waitFor()
    await waitForDeviceState('bardi', 'complete')
    await page
      .getByRole('link', { name: 'Lihat panduan kamera', exact: true })
      .waitFor({ state: 'hidden' })
    assert.equal(
      await cameraRegister.isVisible(),
      true,
      'a complete camera category still allows additional cameras',
    )
    assert.equal(
      await page
        .locator('#device-tabs-bardi .tab-selector__status--complete')
        .count(),
      1,
    )
    await cameraRegister.click()
    await page
      .getByLabel('Nama kamera', { exact: true })
      .fill('Kamera Tambahan')
    await page.locator('details summary').click()
    await page
      .getByLabel('Alamat RTSP', { exact: true })
      .fill('rtsp://camera-extra.invalid/stream')
    await page
      .getByRole('button', { name: 'Tambahkan kamera', exact: true })
      .click()
    await page
      .getByRole('heading', { name: 'Kamera Tambahan', exact: true })
      .waitFor()
    assert.equal(
      await page.locator('.camera-card').count(),
      2,
      'an additional configured camera can be added after setup is complete',
    )
    assert.equal(
      await page
        .locator('#device-tabs-bardi .tab-selector__status--complete')
        .count(),
      1,
    )
    assert.equal(
      await page
        .getByRole('link', { name: 'Lihat panduan kamera', exact: true })
        .count(),
      0,
    )

    // ESP32 guide has its own route and cannot mark setup complete by being read.
    await page.getByRole('tab', { name: /^ESP32/ }).click()
    await waitForDeviceState('esp32', 'incomplete')
    await page
      .getByRole('link', { name: 'Lihat panduan ESP32', exact: true })
      .click()
    await page.locator('.setup-step-carousel').waitFor()
    assert.equal(
      await page.evaluate(() => location.hash),
      '#/devices/setup/esp32',
    )
    assert.equal(await page.locator('.devices-screen').count(), 0)
    assert.equal(await page.locator('form').count(), 0)
    await assertGuideSlides('ESP32', 4)
    await capture('device-guide-esp32-mobile')
    await page
      .getByRole('button', { name: 'Daftarkan perangkat', exact: true })
      .click()
    const espDialog = page.getByRole('dialog')
    await espDialog.waitFor()
    assert.equal(
      await page.locator('#device-tabs-esp32').getAttribute('aria-selected'),
      'true',
    )
    await page.getByRole('button', { name: 'Tutup', exact: true }).click()
    await espDialog.waitFor({ state: 'hidden' })
    await waitForDeviceState('esp32', 'incomplete')

    // Register one ESP32; keep its one-time credential out of screenshots and logs.
    await page
      .getByRole('button', { name: 'Daftarkan perangkat', exact: true })
      .click()
    await page
      .getByLabel('Nama perangkat', { exact: true })
      .fill('ESP32 Pintu Depan')
    await page
      .getByRole('button', { name: 'Daftarkan ESP32', exact: true })
      .click()
    await page
      .getByRole('heading', {
        name: 'Simpan kredensial perangkat',
        exact: true,
      })
      .waitFor()
    const credential = page.getByLabel('Kredensial konfigurasi ESP32', {
      exact: true,
    })
    assert.equal(await credential.getAttribute('type'), 'password')
    const oneTimeValue = await credential.inputValue()
    assert.ok(oneTimeValue.length > 10, 'mock returns a one-time credential')
    assert.equal(
      await page.evaluate(() => location.hash.includes('DEMO-ONLY')),
      false,
    )
    await page
      .getByRole('button', {
        name: 'Selesai dan hapus kredensial',
        exact: true,
      })
      .click()
    assert.equal(
      await page
        .getByLabel('Kredensial konfigurasi ESP32', { exact: true })
        .count(),
      0,
    )
    assert.equal(await page.getByText(oneTimeValue, { exact: true }).count(), 0)
    assert.equal(
      await page.evaluate(() => location.hash.includes('DEMO-ONLY')),
      false,
    )
    await waitForDeviceState('esp32', 'complete')
    assert.equal(
      await page
        .getByRole('link', { name: 'Lihat panduan ESP32', exact: true })
        .count(),
      0,
    )
    assert.equal(
      await page.getByText('ESP32 Pintu Depan', { exact: true }).count(),
      1,
    )

    // A stale inventory read cannot enable a second ESP32; the server-side limit preserves the first.
    await page.evaluate(() => {
      const original = window.harness.services.devices.inventory
      let stale = true
      window.harness.services.devices.inventory = async () => {
        const result = await original()
        if (stale) {
          stale = false
          return { ...result, esp32: null }
        }
        return result
      }
    })
    await route('/deliveries')
    await page
      .getByRole('heading', { name: 'Paket diterima', exact: true })
      .waitFor()
    await route('/devices')
    await waitForDeviceState('esp32', 'incomplete')
    await page
      .getByRole('button', { name: 'Daftarkan perangkat', exact: true })
      .click()
    await page.getByLabel('Nama perangkat', { exact: true }).fill('ESP32 Kedua')
    await page
      .getByRole('button', { name: 'Daftarkan ESP32', exact: true })
      .click()
    await page
      .getByText(
        'Setiap lokasi penerimaan hanya dapat memiliki satu ESP32. Perangkat lama tetap tersimpan.',
        { exact: true },
      )
      .waitFor()
    assert.equal(await page.locator('.camera-card').count(), 2)
    await page.getByRole('button', { name: 'Tutup', exact: true }).click()
    await page.getByText('ESP32 Pintu Depan', { exact: true }).waitFor()
    assert.equal(
      await page.getByText('ESP32 Kedua', { exact: true }).count(),
      0,
    )
    await waitForDeviceState('esp32', 'complete')

    // Compact viewport and enlarged text remain usable; desktop uses the same page.
    await page.setViewportSize({ width: 1280, height: 900 })
    await assertNoPageOverflow('device administration desktop')
    await page.setViewportSize({ width: 320, height: 844 })
    const largeText = await page.addStyleTag({
      content: 'html { font-size: 200% !important; }',
    })
    await capture('devices-large-text')
    await largeText.evaluate((element) => element.remove())
    await page.setViewportSize({ width: 390, height: 844 })

    // An old reference response from an unmounted guide cannot replace the new category.
    await page.evaluate(() => {
      const original = window.harness.services.setup.content
      window.harness.services.setup.content = async (kind) => {
        if (kind === 'esp32') {
          return new Promise((resolve, reject) => {
            window.resolveStaleEsp32Reference = () =>
              original(kind).then(resolve, reject)
          })
        }
        return original(kind)
      }
    })
    await route('/devices/setup/esp32')
    await page.getByText('Memuat referensi…', { exact: true }).waitFor()
    await route('/devices/setup/cameras')
    await page
      .getByText('Belum ada tautan referensi yang disetujui.', { exact: true })
      .waitFor()
    await page.evaluate(() => window.resolveStaleEsp32Reference())
    await page.waitForTimeout(50)
    assert.equal(await page.locator('.device-guide--esp32').count(), 0)
    assert.equal(
      await page
        .getByRole('link', { name: 'Lihat sumber firmware', exact: true })
        .count(),
      0,
    )
    assert.equal(
      await page
        .getByRole('link', { name: 'Baca panduan ESP32', exact: true })
        .count(),
      0,
    )

    // A current setup-reference 401 expires the admin session and removes its guide.
    await route('/deliveries')
    await page
      .getByRole('heading', { name: 'Paket diterima', exact: true })
      .waitFor()
    await page.evaluate(() => {
      window.harness.services.setup.content = async () => {
        throw Object.assign(new Error('unauthorized fixture'), { status: 401 })
      }
    })
    await route('/devices/setup/esp32')
    await page.getByRole('heading', { name: 'Masuk', exact: true }).waitFor()
    assert.equal(await page.evaluate(() => location.hash), '#/login')
    assert.equal(await page.locator('.setup-step-carousel').count(), 0)

    // Members cannot open either admin guide, including through a direct route.
    await login('tetangga')
    await route('/devices/setup/cameras')
    await page
      .getByRole('heading', { name: 'Paket diterima', exact: true })
      .waitFor()
    assert.equal(await page.evaluate(() => location.hash), '#/deliveries')
    assert.equal(await page.locator('.setup-step-carousel').count(), 0)
    assert.deepEqual(errors, [])
    console.log(
      'PASS: device tab relationships and roving keyboard focus, separate ESP32/camera guides with loaded illustrations and touch/keyboard progress, native registration modal focus and cleanup, failed/pending/successful camera registration and selection, one-time ESP32 credential cleanup and duplicate limit, route guards, responsive layout, and no page errors.',
    )
  } finally {
    await browser.close()
  }
})().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
