import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApiClient, apiError } from './client'
import {
  validateRegistration,
  validateShipment,
  type TokenPair,
  type User,
} from './contracts'
import { createApiMock } from './mock'
import { createShipmentServices } from './index'
const user: User = {
  id: 'user-1',
  email: 'test@example.test',
  full_name: 'Test',
  role: 'admin',
  is_active: true,
  created_at: '2026-11-19T00:00:00Z',
}
const tokens = (access = 'access'): TokenPair => ({
  access_token: access,
  refresh_token: 'refresh',
  expires_in: 900,
  refresh_expires_in: 604800,
  user,
})
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status })
const credentials = { email: 'test@example.test', password: 'password12345' }
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
})

describe('API session transport', () => {
  it('uses the signed-in location for ESP provisioning and FCM registration', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        json({
          ...tokens(),
          location_id: 'location-1',
          esp_device_id: 'esp-1',
        }),
      )
      .mockResolvedValueOnce(
        json([{ id: 'location-1', esp_device_id: 'esp-1' }]),
      )
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(
        json({ device_id: 'esp-1', device_key: 'device-key' }),
      )
      .mockResolvedValueOnce(
        json({ device_id: 'push-id', location_id: 'location-1' }),
      )
      .mockResolvedValueOnce(json({ detail: 'removed' }))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    expect(client.locationId?.()).toBe('location-1')
    const esp = await client.devices!.registerEsp32('ESP32')
    expect(esp.credential).toBe('device-key')
    expect(String(fetch.mock.calls[3]?.[0])).toContain(
      '/locations/location-1/esp/credentials',
    )
    await client.push!.upsert({
      installationId: 'one',
      platform: 'android',
      token: 'push-token',
    })
    expect(JSON.parse(String(fetch.mock.calls[4]?.[1]?.body))).toEqual({
      location_id: 'location-1',
      token: 'push-token',
    })
    await client.push!.detach('one')
    expect(String(fetch.mock.calls[5]?.[0])).toContain(
      '/notifications/fcm/unregister',
    )
  })
  it('uses exact paths and maps registration to pending without a session', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(json({ detail: 'Check email' }, 201))
    const client = createApiClient({
      baseUrl: 'https://api.test/api/v1///',
      fetch,
    })
    await client.auth.register({
      email: ' TEST@Example.test ',
      full_name: ' Test ',
      password: credentials.password,
    })
    expect(client.user()).toBeNull()
    expect(fetch.mock.calls[0]?.[0]).toBe(
      'https://api.test/api/v1/auth/register',
    )
    const init = fetch.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(init.body))).toEqual({
      email: credentials.email,
      full_name: 'Test',
      password: credentials.password,
    })
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
  })
  it('shares one refresh between concurrent expired-token requests', async () => {
    let time = 0
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(tokens('new-access')))
      .mockImplementation(() => Promise.resolve(json([])))
    const client = createApiClient({ fetch, now: () => time })
    await client.auth.login(credentials)
    time = 880000
    await Promise.all([client.shipments.list(), client.notifications.list()])
    expect(
      fetch.mock.calls.filter((call) =>
        String(call[0]).endsWith('/auth/refresh'),
      ),
    ).toHaveLength(1)
    for (const [, init] of fetch.mock.calls.slice(2))
      expect(
        new Headers((init as RequestInit).headers).get('Authorization'),
      ).toBe('Bearer new-access')
  })
  it('refreshes a rejected access token and retries once, then ends an invalid session', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json(tokens('new')))
      .mockResolvedValueOnce(json({}, 401))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(client.shipments.list()).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(4)
    expect(client.user()).toBeNull()
  })
  it('does not sign out on 403 or refresh public login failures', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json({}, 403))
    const client = createApiClient({ fetch })
    await expect(client.auth.login(credentials)).rejects.toMatchObject({
      status: 401,
    })
    expect(fetch).toHaveBeenCalledTimes(1)
    await client.auth.login(credentials)
    await expect(client.users.list()).rejects.toMatchObject({ status: 403 })
    expect(client.user()?.id).toBe(user.id)
  })
  it('retains a session on transient refresh failure and permits retry', async () => {
    let time = 0
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockRejectedValueOnce(new TypeError('network'))
      .mockResolvedValueOnce(json(tokens('new')))
      .mockResolvedValueOnce(json([]))
    const client = createApiClient({ fetch, now: () => time })
    await client.auth.login(credentials)
    time = 880000
    await expect(client.shipments.list()).rejects.toMatchObject({
      code: 'connection',
    })
    expect(client.user()).not.toBeNull()
    await expect(client.shipments.list()).resolves.toMatchObject({ items: [] })
  })
  it('clears the session when the refresh token is rejected', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json({}, 401))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(client.auth.refresh()).rejects.toMatchObject({ status: 401 })
    expect(client.user()).toBeNull()
  })
  it('ignores login results after logout', async () => {
    let resolve!: (response: Response) => void
    const fetch = vi.fn(
      () =>
        new Promise<Response>((done) => {
          resolve = done
        }),
    )
    const client = createApiClient({ fetch })
    const login = client.auth.login(credentials)
    client.auth.logout()
    resolve(json(tokens()))
    await expect(login).rejects.toMatchObject({ code: 'cancelled' })
    expect(client.user()).toBeNull()
  })
  it('does not restore a session from storage or a second client', async () => {
    const client = createApiClient({
      fetch: vi.fn().mockResolvedValue(json(tokens())),
    })
    await client.auth.login(credentials)
    expect(createApiClient().user()).toBeNull()
  })
  it('refreshes identity after a self-demotion', async () => {
    const member = { ...user, role: 'member' as const }
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(member))
      .mockResolvedValueOnce(json({ ...tokens('new'), user: member }))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await client.users.role(user.id, 'member')
    expect(client.user()?.role).toBe('member')
    expect(fetch.mock.calls[1]?.[0]).toBe('/api/v1/auth/users/user-1/role')
  })
})

describe('shipments, errors and UI boundary', () => {
  it('finds deep-linked records beyond the first page without inventing a GET by ID', async () => {
    const first = Array.from({ length: 100 }, (_, id) => ({ id: String(id) }))
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(first))
      .mockResolvedValueOnce(json([{ id: 'target' }]))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(client.shipments.find('target')).resolves.toMatchObject({
      id: 'target',
    })
    expect(fetch.mock.calls.slice(1).map((call) => call[0])).toEqual([
      '/api/v1/shipments?limit=100&offset=0',
      '/api/v1/shipments?limit=100&offset=100',
    ])
  })
  it('stops lookup on an exhausted page and supports cancellation', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json([]))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    expect(await client.shipments.find('missing')).toBeNull()
    const controller = new AbortController()
    controller.abort()
    await expect(
      client.shipments.find('missing', controller.signal),
    ).rejects.toBeDefined()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it.each([200, 201])('accepts shipment creation HTTP %s', async (status) => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json({ id: 'created' }, status))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(
      client.shipments.create({ courier: 'JNE', resi_number: ' ab123 ' }),
    ).resolves.toMatchObject({ id: 'created' })
  })
  it('retains identity and maps provider failure', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json({}, 502))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(client.shipments.refresh('id')).rejects.toMatchObject({
      status: 502,
      message: expect.stringContaining('pelacakan'),
    })
    expect(client.user()).not.toBeNull()
  })
  it('maps FastAPI field errors and does not leak validation input or server internals', () => {
    expect(
      apiError(422, {
        detail: [{ loc: ['body', 'email'], msg: 'bad', input: 'secret' }],
      }).fieldErrors,
    ).toEqual({ email: 'Periksa nilai isian ini.' })
    expect(
      apiError(500, { detail: 'database password' }).message,
    ).not.toContain('database')
    expect(apiError(503, {}).message).toContain('Akun mungkin sudah dibuat')
  })
  it('validates UTF-8 password limits and shipment normalization', () => {
    expect(
      validateRegistration({ ...credentials, full_name: ' Test ' }),
    ).toEqual({})
    expect(
      validateRegistration({
        ...credentials,
        full_name: ' ',
        password: 'é'.repeat(37),
      }),
    ).toHaveProperty('password')
    expect(
      validateShipment({ courier: ' JNE ', resi_number: ' ab123 ' }),
    ).toEqual({})
    expect(validateShipment({ courier: '/', resi_number: 'a' })).toHaveProperty(
      'resi_number',
    )
  })
  it('uses the active demo session for device inventory and registration', async () => {
    const client = createApiMock()
    const devices = client.devices!
    await expect(devices.inventory()).rejects.toMatchObject({ status: 401 })
    await client.auth.login({
      email: 'admin@demo.test',
      password: 'demo12345678',
    })
    await devices.registerEsp32('ESP32 demo')
    const device = (await devices.inventory()).esp32!
    expect(device.name).toBe('ESP32 demo')
    await expect(
      devices.renameEsp32(device.id, 'ESP32 teras'),
    ).resolves.toMatchObject({
      esp32: { id: device.id, name: 'ESP32 teras' },
    })
    await client.auth.login({
      email: 'member@demo.test',
      password: 'demo12345678',
    })
    await expect(devices.inventory()).rejects.toMatchObject({ status: 403 })
    await expect(devices.removeEsp32(device.id)).rejects.toMatchObject({
      status: 403,
    })
    await expect(
      devices.updateCamera('camera-demo-porch', { name: 'Kamera teras' }),
    ).rejects.toMatchObject({ status: 403 })
    await expect(
      devices.removeCamera('camera-demo-porch'),
    ).rejects.toMatchObject({
      status: 403,
    })
  })
  it('mock registration stays pending; admin role changes apply without replacing identity', async () => {
    const client = createApiMock()
    await client.auth.register({ ...credentials, full_name: 'Test' })
    expect(client.user()).toBeNull()
    await client.auth.login({
      email: 'admin@demo.test',
      password: 'demo12345678',
    })
    const before = client.user()!.id
    const member = (await client.users.list()).find(
      (item) => item.role === 'member',
    )!
    await client.users.role(member.id, 'admin')
    expect(client.user()!.id).toBe(before)
    await expect(
      client.auth.register({ ...credentials, full_name: 'Test' }),
    ).rejects.toMatchObject({ status: 409 })
    client.auth.logout()
  })
})

describe('screenshot autofill', () => {
  const image = new File(['original screenshot'], 'order.png', {
    type: 'image/png',
  })
  const extracted = {
    resi_number: '000xY-128',
    courier_service: null,
    sender_name: 'Toko Contoh',
    product_names: ['Kotak penyimpanan'],
  }

  it('sends the original file with the existing bearer session and returns partial details', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(extracted))
    const api = createApiClient({ fetch })
    await api.auth.login(credentials)

    await expect(api.shipments.analyzeScreenshot(image)).resolves.toEqual(
      extracted,
    )
    expect(fetch).toHaveBeenLastCalledWith(
      '/api/v1/shipments/analyze-screenshot',
      expect.objectContaining({
        method: 'POST',
        body: image,
        cache: 'no-store',
      }),
    )
    const headers = new Headers(fetch.mock.lastCall?.[1].headers)
    expect(headers.get('Authorization')).toBe('Bearer access')
    expect(headers.get('Content-Type')).toBe('image/png')
  })

  it('cancels the binary request when the review is closed', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockImplementationOnce(
        (_input: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener(
              'abort',
              () => reject(init.signal?.reason),
              { once: true },
            )
          }),
      )
    const api = createApiClient({ fetch })
    await api.auth.login(credentials)
    const controller = new AbortController()
    const analysis = api.shipments.analyzeScreenshot(image, controller.signal)
    controller.abort()

    await expect(analysis).rejects.toMatchObject({ code: 'cancelled' })
  })

  it.each([413, 415, 422, 502, 503, 504])(
    'maps HTTP %i to a screenshot-specific error',
    async (status) => {
      const fetch = vi
        .fn()
        .mockResolvedValueOnce(json(tokens()))
        .mockResolvedValueOnce(json({}, status))
      const api = createApiClient({ fetch })
      await api.auth.login(credentials)

      await expect(
        api.shipments.analyzeScreenshot(image),
      ).rejects.toMatchObject({
        code: 'screenshot_analysis',
        status,
      })
    },
  )
})

describe('foreground notifications', () => {
  it('simulates one camera detection and cancels it when disconnected', async () => {
    vi.useFakeTimers()
    const client = createApiMock({ simulateDetection: true })
    await client.auth.login({
      email: 'member@demo.test',
      password: 'demo12345678',
    })
    const event = vi.fn()
    const handlers = { event, status: vi.fn(), ready: vi.fn() }
    const disconnect = client.notifications.connect(handlers)

    disconnect()
    await vi.advanceTimersByTimeAsync(1000)
    expect(event).not.toHaveBeenCalled()
    expect((await client.shipments.list()).items).toHaveLength(1)

    client.notifications.connect(handlers)
    await vi.advanceTimersByTimeAsync(1000)
    expect(event).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({ shipment_id: 'demo-detected-shipment' }),
    )
    await expect(
      client.shipments.find('demo-detected-shipment'),
    ).resolves.toMatchObject({
      resi_number: 'DEMO-NEW-001',
      source: 'camera',
    })

    client.notifications.connect(handlers)
    await vi.advanceTimersByTimeAsync(1000)
    expect(event).toHaveBeenCalledTimes(1)
  })

  class FakeSocket {
    onmessage: ((event: { data: string }) => void) | null = null
    onclose: ((event: { code: number }) => void) | null = null
    onerror: (() => void) | null = null
    closed = false
    close() {
      this.closed = true
    }
    message(value: unknown) {
      this.onmessage?.({ data: JSON.stringify(value) })
    }
    disconnect(code: number) {
      this.onclose?.({ code })
    }
  }
  const event = {
    id: 'notice-1',
    shipment_id: 'shipment-1',
    title: 'Title',
    message: 'Message',
    created_at: '2026-11-19T00:00:00Z',
  }
  async function setup() {
    vi.useFakeTimers()
    const sockets: FakeSocket[] = []
    const urls: string[] = []
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockImplementation(() => Promise.resolve(json(tokens('renewed'))))
    const client = createApiClient({
      baseUrl: 'https://api.test/api/v1',
      fetch,
      socket: (url) => {
        urls.push(url)
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket as unknown as WebSocket
      },
    })
    await client.auth.login(credentials)
    const handlers = { ready: vi.fn(), event: vi.fn(), status: vi.fn() }
    const disconnect = client.notifications.connect(handlers)
    return { client, sockets, urls, handlers, disconnect, fetch }
  }
  it('authenticates over WSS, ignores malformed data, and deduplicates repeated events', async () => {
    const { sockets, urls, handlers, disconnect } = await setup()
    expect(urls[0]).toBe(
      'wss://api.test/api/v1/notifications/live?token=access',
    )
    sockets[0]!.message({ type: 'ready' })
    sockets[0]!.message({ bad: true })
    sockets[0]!.message(event)
    sockets[0]!.message(event)
    expect(handlers.ready).toHaveBeenCalledOnce()
    expect(handlers.event).toHaveBeenCalledOnce()
    disconnect()
    expect(sockets[0]!.closed).toBe(true)
  })
  it('recovers from Redis failure and asks HTTP consumers to resync after reconnect', async () => {
    const { sockets, handlers, disconnect } = await setup()
    sockets[0]!.message({ type: 'ready' })
    sockets[0]!.disconnect(1013)
    await vi.advanceTimersByTimeAsync(1000)
    expect(sockets).toHaveLength(2)
    sockets[1]!.message({ type: 'ready' })
    expect(handlers.ready).toHaveBeenCalledTimes(2)
    disconnect()
  })
  it('renews at the token deadline and closes sockets on logout', async () => {
    const { client, sockets, urls, disconnect } = await setup()
    await vi.advanceTimersByTimeAsync(870001)
    expect(sockets[0]!.closed).toBe(true)
    expect(urls.at(-1)).toContain('token=renewed')
    client.auth.logout()
    expect(sockets.at(-1)!.closed).toBe(true)
    const count = sockets.length
    await vi.advanceTimersByTimeAsync(900000)
    expect(sockets).toHaveLength(count)
    disconnect()
  })
  it('refreshes only once after consecutive authentication closures', async () => {
    const { sockets, fetch, disconnect } = await setup()
    sockets[0]!.disconnect(4401)
    await vi.advanceTimersByTimeAsync(1001)
    sockets.at(-1)!.disconnect(4401)
    await vi.advanceTimersByTimeAsync(40000)
    expect(
      fetch.mock.calls.filter((call) =>
        String(call[0]).endsWith('/auth/refresh'),
      ),
    ).toHaveLength(1)
    disconnect()
  })
  it('pauses in background and reconnects when visible', async () => {
    const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
    vi.stubGlobal('document', doc)
    const { sockets, disconnect } = await setup()
    doc.visibilityState = 'hidden'
    doc.dispatchEvent(new Event('visibilitychange'))
    expect(sockets[0]!.closed).toBe(true)
    await vi.advanceTimersByTimeAsync(60000)
    expect(sockets).toHaveLength(1)
    doc.visibilityState = 'visible'
    doc.dispatchEvent(new Event('visibilitychange'))
    expect(sockets).toHaveLength(2)
    disconnect()
  })
})

describe('API integration regression coverage', () => {
  it('refreshes a cached detail from HTTP when explicitly reloaded', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json([{ id: 'target', summary: 'old' }]))
      .mockResolvedValueOnce(json([{ id: 'target', summary: 'new' }]))
    const client = createApiClient({ fetch })
    await client.auth.login(credentials)
    await expect(client.shipments.find('target')).resolves.toMatchObject({
      summary: 'old',
    })
    await expect(client.shipments.find('target')).resolves.toMatchObject({
      summary: 'old',
    })
    await expect(
      client.shipments.find('target', undefined, true),
    ).resolves.toMatchObject({ summary: 'new' })
    expect(fetch).toHaveBeenCalledTimes(3)
  })
  it.each([403, 404, 409])(
    'does not change current identity when role update returns HTTP %s',
    async (status) => {
      const fetch = vi
        .fn()
        .mockResolvedValueOnce(json(tokens()))
        .mockResolvedValueOnce(json({}, status))
      const client = createApiClient({ fetch })
      await client.auth.login(credentials)
      await expect(client.users.role(user.id, 'member')).rejects.toMatchObject({
        status,
      })
      expect(client.user()?.role).toBe('admin')
    },
  )
  it('keeps resend public and registration failure unauthenticated', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({}, 503))
      .mockResolvedValueOnce(json({ detail: 'generic' }))
    const client = createApiClient({ fetch })
    await expect(
      client.auth.register({ ...credentials, full_name: 'Test' }),
    ).rejects.toMatchObject({ status: 503 })
    await expect(client.auth.resend(credentials)).resolves.toEqual({
      detail: 'generic',
    })
    expect(client.user()).toBeNull()
    expect(fetch.mock.calls[1]?.[0]).toBe('/api/v1/auth/resend-verification')
  })
  it('ignores the mock flag in production mode', async () => {
    vi.stubEnv('DEV', false)
    vi.stubEnv('VITE_APP_MODE', 'mock')
    expect((await createShipmentServices()).mode).toBe('live')
  })
  it('selects API-compatible mocks only in development', async () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_APP_MODE', 'mock')
    const services = await createShipmentServices()
    expect(services.mode).toBe('mock')
    await services.auth.login({
      email: 'member@demo.test',
      password: 'demo12345678',
    })
    await expect(services.shipments.list()).resolves.toMatchObject({
      items: [{ resi_number: 'DEMO123456' }],
    })
  })
})
