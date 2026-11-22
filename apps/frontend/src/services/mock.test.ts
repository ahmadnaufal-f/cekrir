import { describe, expect, it } from 'vitest'
import { createMockHarness } from './mock'
import { MOCK_DEMO_ACCOUNTS, MOCK_DELIVERY_IDS } from './mock-fixtures'

async function signInAdmin(
  harness: ReturnType<typeof createMockHarness>,
): Promise<void> {
  await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.admin)
}

describe('mock services', () => {
  it('provides demo accounts and every independent photo/tracking state combination', async () => {
    const harness = createMockHarness()
    const admin = await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.admin)

    expect(admin.role).toBe('admin')
    const page = await harness.services.deliveries.list()
    expect(page.items).toHaveLength(9)
    expect(page.nextCursor).toBeNull()
    expect(
      new Set(
        page.items.map(
          (delivery) => `${delivery.photoState}/${delivery.trackingState}`,
        ),
      ).size,
    ).toBe(9)
    expect(page.items[0]?.id).toBe(MOCK_DELIVERY_IDS.complete)

    const complete = await harness.services.deliveries.detail(
      MOCK_DELIVERY_IDS.complete,
    )
    expect(complete.tracking?.events).toHaveLength(1)
    expect(complete.trackingNumber).toMatch(/^DEMO-SPX-/)
    expect(complete.photoContentPath).toBe('mock:demo-delivery.svg')
    const image = await harness.services.deliveries.photo(
      MOCK_DELIVERY_IDS.complete,
    )
    expect(image.type).toBe('image/svg+xml')
    expect(await image.text()).toContain('BUKAN FOTO CCTV')

    await harness.services.auth.logout()
    expect(
      (await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.member)).role,
    ).toBe('member')
    await harness.services.auth.logout()
    expect(
      (await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.otherHousehold))
        .householdId,
    ).toBe('household-tetangga')
  })

  it('paginates in newest-first order with stable, non-repeating cursor IDs', async () => {
    const harness = createMockHarness({ pageSize: 3 })
    await signInAdmin(harness)
    const ids: string[] = []
    let cursor: string | undefined
    do {
      const page = await harness.services.deliveries.list(cursor)
      ids.push(...page.items.map((item) => item.id))
      cursor = page.nextCursor ?? undefined
    } while (cursor)

    expect(ids).toHaveLength(9)
    expect(new Set(ids).size).toBe(9)
    expect(ids[0]).toBe(MOCK_DELIVERY_IDS.complete)
    expect(ids[8]).toBe('delivery-demo-photo-unavailable-tracking-pending')
  })

  it('searches the full household repository before applying pagination', async () => {
    const harness = createMockHarness({ pageSize: 3 })
    await signInAdmin(harness)

    expect(
      await harness.services.deliveries.list(undefined, { search: '  \t ' }),
    ).toEqual(await harness.services.deliveries.list())

    const page = await harness.services.deliveries.list(undefined, {
      search: 'DEMO-SPX-1009',
    })

    expect(page.items.map((delivery) => delivery.trackingNumber)).toEqual([
      'DEMO-SPX-1009',
    ])
    expect(page.nextCursor).toBeNull()
  })

  it('matches trimmed case-insensitive multiword courier and resi searches literally', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)

    const multiword = await harness.services.deliveries.list(undefined, {
      search: '  1009   EXPRESS  ',
    })
    expect(multiword.items.map((delivery) => delivery.trackingNumber)).toEqual([
      'DEMO-SPX-1009',
    ])

    const courierCode = await harness.services.deliveries.list(undefined, {
      search: ' SPX-DEMO ',
    })
    expect(courierCode.items).toHaveLength(9)

    const courierName = await harness.services.deliveries.list(undefined, {
      search: 'SPX Express (demo)',
    })
    expect(courierName.items).toHaveLength(9)

    const regexMetacharacters = await harness.services.deliveries.list(
      undefined,
      { search: 'SPX.*demo' },
    )
    expect(regexMetacharacters.items).toEqual([])

    const normalizedUnicode = await harness.services.deliveries.list(
      undefined,
      { search: 'ＤＥＭＯ-ＳＰＸ-１００９' },
    )
    expect(
      normalizedUnicode.items.map((delivery) => delivery.trackingNumber),
    ).toEqual(['DEMO-SPX-1009'])
  })

  it('keeps search cursors stable within their filtered result set', async () => {
    const harness = createMockHarness({ pageSize: 3 })
    await signInAdmin(harness)
    const ids: string[] = []
    let cursor: string | undefined
    do {
      const page = await harness.services.deliveries.list(cursor, {
        search: '100',
      })
      ids.push(...page.items.map((item) => item.id))
      cursor = page.nextCursor ?? undefined
    } while (cursor)

    expect(ids).toHaveLength(9)
    expect(new Set(ids).size).toBe(9)
    expect(ids[0]).toBe(MOCK_DELIVERY_IDS.complete)
    expect(ids[8]).toBe('delivery-demo-photo-unavailable-tracking-pending')
  })

  it('validates search input and rejects a cursor outside the current filtered set', async () => {
    const harness = createMockHarness({ pageSize: 3 })
    await signInAdmin(harness)

    await expect(
      harness.services.deliveries.list(undefined, { search: 42 } as never),
    ).rejects.toMatchObject({
      status: 422,
      fieldErrors: { search: expect.any(String) },
    })
    await expect(
      harness.services.deliveries.list(undefined, 'invalid query' as never),
    ).rejects.toMatchObject({
      status: 422,
      fieldErrors: { search: expect.any(String) },
    })
    await expect(
      harness.services.deliveries.list(undefined, { search: 'x'.repeat(201) }),
    ).rejects.toMatchObject({
      status: 422,
      fieldErrors: { search: expect.any(String) },
    })

    const broad = await harness.services.deliveries.list(undefined, {
      search: '100',
    })
    await expect(
      harness.services.deliveries.list(broad.nextCursor ?? undefined, {
        search: '1009',
      }),
    ).rejects.toMatchObject({ status: 400 })
  })

  it('counts all household deliveries independently of page size and requested household IDs', async () => {
    const harness = createMockHarness({ pageSize: 3 })
    const query = {
      date: '2026-11-16',
      timeZone: 'Asia/Jakarta',
      householdId: 'household-tetangga',
    }

    await expect(
      harness.services.deliveries.totals(query),
    ).rejects.toMatchObject({ status: 401 })
    await signInAdmin(harness)

    expect(await harness.services.deliveries.totals(query)).toEqual({
      date: '2026-11-16',
      timeZone: 'Asia/Jakarta',
      receivedToday: 0,
      receivedAllTime: 9,
    })
    expect((await harness.services.deliveries.list()).items).toHaveLength(3)
    expect(
      (
        await harness.services.deliveries.list(undefined, {
          search: 'DEMO-SPX-1009',
        })
      ).items,
    ).toHaveLength(1)
    expect(await harness.services.deliveries.totals(query)).toMatchObject({
      receivedAllTime: 9,
    })

    await harness.services.auth.logout()
    await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.otherHousehold)
    expect(await harness.services.deliveries.totals(query)).toMatchObject({
      receivedToday: 0,
      receivedAllTime: 1,
    })
  })

  it('counts scanned timestamps on the requested calendar day in the given time zone', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)

    expect(
      await harness.services.deliveries.totals({
        date: '2026-11-14',
        timeZone: 'Pacific/Honolulu',
      }),
    ).toMatchObject({ receivedToday: 9, receivedAllTime: 9 })
  })

  it('rejects impossible calendar dates and unknown time zones', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)

    await expect(
      harness.services.deliveries.totals({
        date: '2026-02-30',
        timeZone: 'UTC',
      }),
    ).rejects.toMatchObject({
      status: 422,
      fieldErrors: { date: expect.any(String) },
    })
    await expect(
      harness.services.deliveries.totals({
        date: '2026-11-16',
        timeZone: 'Mars/Olympus',
      }),
    ).rejects.toMatchObject({
      status: 422,
      fieldErrors: { timeZone: expect.any(String) },
    })
  })

  it('requires a session and scopes delivery data to the authenticated household', async () => {
    const harness = createMockHarness()
    await expect(harness.services.deliveries.list()).rejects.toMatchObject({
      status: 401,
    })
    await signInAdmin(harness)
    expect(
      (
        await harness.services.deliveries.list(undefined, {
          search: 'DEMO-SPX-2001',
        })
      ).items,
    ).toEqual([])
    await expect(
      harness.services.deliveries.detail('delivery-tetangga-complete'),
    ).rejects.toMatchObject({ status: 403 })
    await expect(
      harness.services.deliveries.detail('missing-delivery'),
    ).rejects.toMatchObject({ status: 404 })
    await expect(
      harness.services.deliveries.photo('delivery-tetangga-complete'),
    ).rejects.toMatchObject({ status: 403 })
    await harness.services.auth.logout()
    await harness.services.auth.login(MOCK_DEMO_ACCOUNTS.otherHousehold)
    expect(
      (
        await harness.services.deliveries.list(undefined, {
          search: 'DEMO-SPX-1009',
        })
      ).items,
    ).toEqual([])
    expect(
      (
        await harness.services.deliveries.list(undefined, {
          search: 'DEMO-SPX-2001',
        })
      ).items,
    ).toHaveLength(1)
    expect(
      (await harness.services.deliveries.detail('delivery-tetangga-complete'))
        .householdId,
    ).toBe('household-tetangga')

    harness.controls.expireSession()
    await expect(
      harness.services.deliveries.totals({
        date: '2026-11-16',
        timeZone: 'UTC',
      }),
    ).rejects.toMatchObject({ status: 401 })
    await expect(harness.services.devices.inventory()).rejects.toMatchObject({
      status: 401,
    })
    expect(await harness.services.auth.restore()).toBeNull()
    harness.controls.reset()
    expect(await harness.services.auth.restore()).toBeNull()
    await expect(harness.services.deliveries.list()).rejects.toMatchObject({
      status: 401,
    })
  })

  it('creates an empty signup household and a usable member without replacing the admin session', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const admin = await harness.services.auth.signup({
      displayName: 'Rumah Baru',
      email: 'owner@example.test',
      householdName: 'Rumah Baru',
      password: 'local-pass',
    })
    expect(admin.role).toBe('admin')
    expect(await harness.services.deliveries.list()).toEqual({
      items: [],
      nextCursor: null,
    })
    expect(
      await harness.services.deliveries.totals({
        date: '2026-11-16',
        timeZone: 'UTC',
      }),
    ).toEqual({
      date: '2026-11-16',
      timeZone: 'UTC',
      receivedToday: 0,
      receivedAllTime: 0,
    })
    expect(await harness.services.members.list()).toEqual([])
    expect((await harness.services.devices.inventory()).esp32).toBeNull()

    const member = await harness.services.members.create({
      displayName: 'Anggota Baru',
      loginId: 'helper',
      initialPassword: 'member-pass',
    })
    expect(member.role).toBe('member')
    expect(member.householdId).toBe(admin.householdId)
    expect(await harness.services.auth.restore()).toMatchObject({
      id: admin.id,
      role: 'admin',
    })
    await harness.services.auth.logout()
    expect(
      await harness.services.auth.login({
        loginId: 'helper',
        password: 'member-pass',
      }),
    ).toMatchObject({
      id: member.id,
      role: 'member',
      householdId: admin.householdId,
    })
    await expect(harness.services.members.list()).rejects.toMatchObject({
      status: 403,
    })
    await expect(harness.services.devices.inventory()).rejects.toMatchObject({
      status: 403,
    })
  })

  it('keeps the ESP32 limit and prior camera selection on failures, without echoing camera credentials', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const created = await harness.services.devices.registerEsp32('Papan Demo')
    expect(created.inventory.esp32?.name).toBe('Papan Demo')
    expect(created.credential).toContain('DEMO-ONLY-NOT-VALID')
    await expect(
      harness.services.devices.registerEsp32('Papan Kedua'),
    ).rejects.toMatchObject({ status: 409 })
    expect((await harness.services.devices.inventory()).esp32).toEqual(
      created.inventory.esp32,
    )

    const cameraInput = {
      name: 'Kamera Tambahan',
      connection: {
        url: 'rtsp://demo.invalid/stream',
        username: 'demo-user',
        password: 'never-echo-this',
      },
    }
    const inventory = await harness.services.devices.registerCamera(cameraInput)
    expect(JSON.stringify(inventory)).not.toContain(
      cameraInput.connection.password,
    )
    const firstId = inventory.cameras[0]!.id
    const secondId = inventory.cameras[1]!.id
    expect(
      (await harness.services.devices.selectCamera(firstId))
        .selectedDeliveryCameraId,
    ).toBe(firstId)
    harness.controls.failNext('camera-selection')
    await expect(
      harness.services.devices.selectCamera(secondId),
    ).rejects.toMatchObject({ status: 503 })
    expect(
      (await harness.services.devices.inventory()).selectedDeliveryCameraId,
    ).toBe(firstId)
  })

  it('returns real scaffold references and leaves the BARDI guide pending', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const esp32 = await harness.services.setup.content('esp32')
    expect(esp32).toMatchObject({
      readiness: 'scaffold',
      sourceUrl: expect.stringContaining('/apps/esp32/src/main.cpp'),
      guideUrl: expect.stringContaining('/apps/esp32/README.md'),
    })
    expect(await harness.services.setup.content('bardi')).toEqual({
      kind: 'bardi',
      readiness: 'pending',
      sourceUrl: null,
      guideUrl: null,
    })
  })

  it('renames and removes only the current ESP32 and leaves camera settings intact', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const { devices } = harness.services
    const created = await devices.registerEsp32('Papan Demo')
    const device = created.inventory.esp32!
    const selected = await devices.selectCamera(
      created.inventory.cameras[0]!.id,
    )

    await expect(devices.renameEsp32(device.id, '   ')).rejects.toMatchObject({
      status: 422,
    })
    harness.controls.failNext('esp32-rename')
    await expect(devices.renameEsp32(device.id, 'Pintu')).rejects.toMatchObject(
      {
        status: 503,
      },
    )
    expect((await devices.inventory()).esp32).toEqual(device)
    await expect(devices.renameEsp32(device.id, ' Pintu ')).resolves.toEqual({
      ...selected,
      esp32: { ...device, name: 'Pintu' },
    })

    harness.controls.failNext('esp32-removal')
    await expect(devices.removeEsp32(device.id)).rejects.toMatchObject({
      status: 503,
    })
    expect((await devices.inventory()).esp32?.id).toBe(device.id)
    await expect(devices.removeEsp32(device.id)).resolves.toEqual({
      ...selected,
      esp32: null,
    })
    const replacement = await devices.registerEsp32('Papan Baru')
    expect(replacement.inventory.esp32?.id).not.toBe(device.id)
    await expect(devices.removeEsp32(device.id)).rejects.toMatchObject({
      status: 404,
    })
    expect((await devices.inventory()).esp32).toEqual(
      replacement.inventory.esp32,
    )
  })

  it('updates camera details without exposing credentials or changing the selected camera', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const { devices } = harness.services
    const { cameras } = await devices.inventory()
    const camera = cameras.find(
      ({ configurationState }) => configurationState === 'incomplete',
    )!
    const selected = await devices.selectCamera(camera.id)

    harness.controls.failNext('camera-update')
    await expect(
      devices.updateCamera(camera.id, { name: 'Garasi' }),
    ).rejects.toMatchObject({
      status: 503,
    })
    expect(await devices.inventory()).toEqual(selected)
    const renamed = await devices.updateCamera(camera.id, { name: ' Garasi ' })
    expect(renamed.selectedDeliveryCameraId).toBe(camera.id)
    expect(renamed.cameras.find(({ id }) => id === camera.id)).toEqual({
      ...camera,
      name: 'Garasi',
    })
    const updated = await devices.updateCamera(camera.id, {
      name: 'Garasi',
      connection: {
        url: 'rtsp://demo.invalid/stream',
        password: 'cctv-demo-password',
      },
    })
    expect(updated.selectedDeliveryCameraId).toBe(camera.id)
    expect(updated.cameras.find(({ id }) => id === camera.id)).toMatchObject({
      name: 'Garasi',
      configurationState: 'configured',
      verificationState: 'not_tested',
    })
    expect(JSON.stringify(updated)).not.toContain('cctv-demo-password')
    expect(await devices.inventory()).toEqual(updated)
  })

  it('clears the delivery selection only when the selected camera is removed', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const { devices } = harness.services
    const [porch, garage] = (await devices.inventory()).cameras
    const selected = await devices.selectCamera(porch!.id)

    harness.controls.failNext('camera-removal')
    await expect(devices.removeCamera(porch!.id)).rejects.toMatchObject({
      status: 503,
    })
    expect(await devices.inventory()).toEqual(selected)
    expect(await devices.removeCamera(garage!.id)).toMatchObject({
      cameras: [porch],
      selectedDeliveryCameraId: porch!.id,
    })
    expect(await devices.removeCamera(porch!.id)).toMatchObject({
      cameras: [],
      selectedDeliveryCameraId: null,
    })
    await expect(
      devices.updateCamera(garage!.id, { name: 'Garasi' }),
    ).rejects.toMatchObject({
      status: 404,
    })
  })

  it('injects one-shot push failures and separates unavailable resources from delivery events', async () => {
    const harness = createMockHarness()
    await signInAdmin(harness)
    const registration = {
      installationId: 'demo-installation',
      platform: 'android' as const,
      token: 'demo-token',
    }

    harness.controls.failNext('push-upsert')
    await expect(
      harness.services.push.upsert(registration),
    ).rejects.toMatchObject({ status: 503 })
    await expect(
      harness.services.push.upsert(registration),
    ).resolves.toBeUndefined()
    harness.controls.failNext('push-detach')
    await expect(
      harness.services.push.detach(registration.installationId),
    ).rejects.toMatchObject({ status: 503 })
    await expect(
      harness.services.push.detach(registration.installationId),
    ).resolves.toBeUndefined()

    const bothFailed = await harness.services.deliveries.detail(
      MOCK_DELIVERY_IDS.bothUnavailable,
    )
    expect(bothFailed.trackingNumber).toMatch(/^DEMO-SPX-/)
    expect(bothFailed.photoState).toBe('unavailable')
    expect(bothFailed.trackingState).toBe('unavailable')
    await expect(
      harness.services.deliveries.photo(MOCK_DELIVERY_IDS.bothUnavailable),
    ).rejects.toMatchObject({ code: 'PHOTO_UNAVAILABLE', status: 503 })
    await expect(
      harness.services.deliveries.photo(MOCK_DELIVERY_IDS.pending),
    ).rejects.toMatchObject({ code: 'PHOTO_PENDING', status: 425 })
  })
})
