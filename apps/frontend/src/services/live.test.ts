import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createAuthorizedTransport,
  createLiveServices,
  createMemoryCredentialStore,
} from './live'
import { ServiceError } from './contracts'
import { createServices } from './index'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('authorized transport', () => {
  it('honours Retry-After before making another network request', async () => {
    vi.useFakeTimers()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('{}', { status: 429, headers: { 'Retry-After': '2' } }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })))
    vi.stubGlobal('fetch', fetch)
    const request = createAuthorizedTransport(
      '/api/v1',
      createMemoryCredentialStore(),
    )
    await expect(request('/deliveries')).rejects.toMatchObject({ status: 429 })
    await expect(request('/deliveries')).rejects.toMatchObject({
      status: 429,
      retryAfter: '2',
    })
    expect(fetch).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(2000)
    await expect(request('/deliveries')).resolves.toEqual({ ok: true })
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it('sends bearer authorization and returns protected photo bytes', async () => {
    const credentials = createMemoryCredentialStore()
    credentials.write('session-secret')
    const bytes = new Uint8Array([0xff, 0xd8, 0x00, 0xff])
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(bytes, { headers: { 'Content-Type': 'image/jpeg' } }),
      )
    vi.stubGlobal('fetch', fetch)

    const request = createAuthorizedTransport(
      'https://api.example.test///',
      credentials,
    )
    const photo = await request<Blob>(
      '/v1/deliveries/fixture-id/photo',
      {},
      true,
    )

    expect(fetch).toHaveBeenCalledOnce()
    const [url, init] = fetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('https://api.example.test/v1/deliveries/fixture-id/photo')
    expect(new Headers(init.headers).get('Authorization')).toBe(
      'Bearer session-secret',
    )
    expect(init.signal).toBeInstanceOf(AbortSignal)
    expect(photo).toBeInstanceOf(Blob)
    expect([...new Uint8Array(await photo.arrayBuffer())]).toEqual([...bytes])
    expect(photo.type).toBe('image/jpeg')
  })

  it('clears credentials and signals the session handler on 401', async () => {
    const credentials = createMemoryCredentialStore()
    credentials.write('expired-session')
    const onUnauthorized = vi.fn()
    const fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: 'session_expired' }), {
        status: 401,
      }),
    )
    vi.stubGlobal('fetch', fetch)

    const request = createAuthorizedTransport(
      'https://api.example.test',
      credentials,
      onUnauthorized,
    )

    await expect(request('/v1/me')).rejects.toMatchObject({
      code: 'session_expired',
      status: 401,
      message: 'Sesi berakhir. Silakan masuk lagi.',
    })
    expect(fetch).toHaveBeenCalledOnce()
    expect(onUnauthorized).toHaveBeenCalledOnce()
    expect(credentials.read()).toBeNull()
  })

  it.each([
    [403, 'forbidden', 'Anda tidak memiliki akses ke paket ini.'],
    [404, 'missing_delivery', 'Paket tidak ditemukan.'],
    [409, 'esp32_limit', 'Hanya satu ESP32 yang dapat didaftarkan.'],
    [422, 'invalid_form', 'Periksa isian formulir.'],
    [429, 'rate_limited', 'Terlalu banyak permintaan. Coba lagi nanti.'],
  ] as const)(
    'maps HTTP %i to its user-facing status and server code',
    async (status, code, message) => {
      const fetch = vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code,
            fieldErrors: { loginId: 'Tidak valid', ignored: 4 },
          }),
          {
            status,
            headers: status === 429 ? { 'Retry-After': '37' } : undefined,
          },
        ),
      )
      vi.stubGlobal('fetch', fetch)
      const request = createAuthorizedTransport(
        'https://api.example.test',
        createMemoryCredentialStore(),
      )

      await expect(request('/v1/example')).rejects.toMatchObject({
        code,
        status,
        message,
        fieldErrors: { loginId: 'Tidak valid' },
        retryAfter: status === 429 ? '37' : undefined,
      })
    },
  )

  it.each(['unreachable server', 'request timeout'])(
    'reports %s as a connection error without fabricating a response',
    async (failure) => {
      const reason =
        failure === 'request timeout'
          ? new DOMException('The request timed out', 'TimeoutError')
          : new TypeError('Failed to fetch')
      const fetch = vi.fn().mockRejectedValue(reason)
      vi.stubGlobal('fetch', fetch)
      const request = createAuthorizedTransport(
        'https://api.example.test',
        createMemoryCredentialStore(),
      )

      await expect(request('/v1/deliveries')).rejects.toMatchObject({
        code: 'connection',
        status: 0,
        message:
          'Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.',
      })
      expect(fetch).toHaveBeenCalledOnce()
    },
  )

  it('rejects an absolute or protocol-relative path before making a request', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const request = createAuthorizedTransport(
      'https://api.example.test',
      createMemoryCredentialStore(),
    )

    await expect(
      request('https://other.example.test/v1/me'),
    ).rejects.toBeInstanceOf(ServiceError)
    await expect(request('//other.example.test/v1/me')).rejects.toMatchObject({
      code: 'invalid_path',
    })
    expect(fetch).not.toHaveBeenCalled()
  })
})

describe('live service selection', () => {
  it('uses live services when the development mock flag is absent', async () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_APP_MODE', '')
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)

    const services = await createServices()

    expect(services.mode).toBe('live')
    await expect(services.deliveries.list()).rejects.toMatchObject({
      code: 'integration_unavailable',
      status: 501,
    })
    await expect(
      services.deliveries.totals({ date: '2026-11-16', timeZone: 'UTC' }),
    ).rejects.toMatchObject({ code: 'integration_unavailable', status: 501 })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('leaves remaining unsupported live operations explicit and makes no guessed network calls', async () => {
    const services = createLiveServices()
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const operations: Array<() => Promise<unknown>> = [
      () =>
        services.auth.signup({
          displayName: 'Admin',
          email: 'admin@example.test',
          householdName: 'Home',
          password: 'secret',
        }),
      () => services.deliveries.list(),
      () => services.deliveries.list(undefined, { search: 'DEMO-SPX-1009' }),
      () => services.deliveries.totals({ date: '2026-11-16', timeZone: 'UTC' }),
      () => services.deliveries.detail('opaque-delivery-id'),
      () => services.deliveries.photo('opaque-delivery-id'),
      () => services.devices.renameEsp32('opaque-esp32-id', 'Pintu'),
      () => services.devices.removeEsp32('opaque-esp32-id'),
      () =>
        services.devices.updateCamera('opaque-camera-id', { name: 'Porch' }),
      () => services.devices.removeCamera('opaque-camera-id'),
      () => services.devices.selectCamera('opaque-camera-id'),
      () => services.members.list(),
      () =>
        services.members.create({
          displayName: 'Member',
          loginId: 'member',
          initialPassword: 'secret',
        }),
      () => services.setup.content('bardi'),
    ]

    expect(services.mode).toBe('live')
    for (const operation of operations) {
      await expect(operation()).rejects.toMatchObject({
        code: 'integration_unavailable',
        status: 501,
      })
    }
    expect(fetch).not.toHaveBeenCalled()
  })
})
