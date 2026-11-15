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

  it('requires a session and scopes delivery data to the authenticated household', async () => {
    const harness = createMockHarness()
    await expect(harness.services.deliveries.list()).rejects.toMatchObject({
      status: 401,
    })
    await signInAdmin(harness)
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
      (await harness.services.deliveries.detail('delivery-tetangga-complete'))
        .householdId,
    ).toBe('household-tetangga')

    harness.controls.expireSession()
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
