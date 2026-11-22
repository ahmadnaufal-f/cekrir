import { Capacitor } from '@capacitor/core'
import { ServiceError } from '../../services/contracts'
import type { CameraInput, DeviceInventory } from '../../types/app'
import type {
  ApiServices,
  TokenPair,
  User,
  Shipment,
  PackageNotification,
  Page,
} from './contracts'

const messages: Record<number, string> = {
  400: 'Permintaan tidak valid.',
  401: 'Sesi berakhir. Silakan masuk lagi.',
  403: 'Anda tidak memiliki izin untuk tindakan ini.',
  404: 'Data tidak ditemukan.',
  409: 'Data bertentangan dengan catatan yang sudah ada.',
  422: 'Periksa isian formulir.',
  429: 'Terlalu banyak permintaan. Coba lagi nanti.',
  502: 'Layanan pelacakan tidak tersedia. Coba lagi nanti.',
  503: 'Layanan email tidak tersedia. Akun mungkin sudah dibuat; coba kirim ulang verifikasi atau masuk.',
}
export function apiError(status: number, body: unknown): ServiceError {
  const fields: Record<string, string> = {}
  const detail =
    body && typeof body === 'object' && 'detail' in body ? body.detail : null
  if (Array.isArray(detail))
    for (const error of detail) {
      if (error && Array.isArray(error.loc)) {
        const key = error.loc
          .filter((v: unknown) => v !== 'body' && v !== 'query')
          .join('.')
        if (key) fields[key] = 'Periksa nilai isian ini.'
      }
    }
  return new ServiceError(
    'http_error',
    messages[status] || 'Permintaan gagal. Silakan coba lagi.',
    status,
    fields,
  )
}
export interface ClientOptions {
  baseUrl?: string
  fetch?: typeof fetch
  socket?: (url: string) => WebSocket
  now?: () => number
}
export function createApiClient(options: ClientOptions = {}): ApiServices {
  const base = (
    options.baseUrl ||
    import.meta.env.VITE_API_BASE_URL ||
    '/api/v1'
  ).replace(/\/+$/, '')
  const fetcher: typeof fetch =
    options.fetch || ((...args) => globalThis.fetch(...args))
  const now = options.now || Date.now
  let pair: TokenPair | null = null
  let expiresAt = 0
  let refreshExpiresAt = 0
  let generation = 0
  let refreshWork: Promise<User> | null = null
  const listeners = new Set<(user: User | null) => void>()
  const controllers = new Set<AbortController>()
  const cache = new Map<string, Shipment>()
  function notify() {
    for (const listener of listeners) listener(pair?.user || null)
  }
  function clear() {
    generation++
    pair = null
    refreshWork = null
    cache.clear()
    for (const controller of controllers) controller.abort()
    controllers.clear()
    notify()
  }
  function accept(value: TokenPair, version: number) {
    if (version !== generation)
      throw new ServiceError('cancelled', 'Permintaan dibatalkan.')
    pair = value
    expiresAt = now() + value.expires_in * 1000
    refreshExpiresAt = now() + value.refresh_expires_in * 1000
    notify()
    return value.user
  }
  async function raw<T>(
    path: string,
    init: RequestInit = {},
    token?: string,
  ): Promise<T> {
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('://'))
      throw new ServiceError('configuration', 'Alamat API tidak valid.')
    if (Capacitor.isNativePlatform() && !base.startsWith('https://'))
      throw new ServiceError(
        'configuration',
        'Gunakan alamat API HTTPS untuk aplikasi mobile.',
      )
    const controller = new AbortController()
    controllers.add(controller)
    const headers = new Headers(init.headers)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    if (init.body && !headers.has('Content-Type'))
      headers.set('Content-Type', 'application/json')
    try {
      const response = await fetcher(`${base}${path}`, {
        ...init,
        headers,
        signal: AbortSignal.any([
          controller.signal,
          AbortSignal.timeout(15000),
          ...(init.signal ? [init.signal] : []),
        ]),
      })
      const body: unknown = await response.json().catch(() => null)
      if (!response.ok) throw apiError(response.status, body)
      return body as T
    } catch (error) {
      if (error instanceof ServiceError) throw error
      if (controller.signal.aborted || init.signal?.aborted)
        throw new ServiceError('cancelled', 'Permintaan dibatalkan.')
      throw new ServiceError(
        'connection',
        'Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.',
      )
    } finally {
      controllers.delete(controller)
    }
  }
  const post = (body: unknown): RequestInit => ({
    method: 'POST',
    body: JSON.stringify(body),
  })
  async function refresh(): Promise<User> {
    if (refreshWork) return refreshWork
    if (!pair || now() >= refreshExpiresAt) {
      clear()
      throw apiError(401, null)
    }
    const version = generation
    const token = pair.refresh_token
    const work = raw<TokenPair>('/auth/refresh', post({ refresh_token: token }))
      .then((value) => accept(value, version))
      .catch((error) => {
        if (
          version === generation &&
          error instanceof ServiceError &&
          error.status === 401
        )
          clear()
        throw error
      })
    refreshWork = work
    try {
      return await work
    } finally {
      if (refreshWork === work) refreshWork = null
    }
  }
  async function authorized<T>(path: string, init?: RequestInit): Promise<T> {
    const version = generation
    if (!pair) throw apiError(401, null)
    if (now() >= expiresAt - 30000) await refresh()
    const sentToken = pair?.access_token
    try {
      const result = await raw<T>(path, init, sentToken)
      if (version !== generation)
        throw new ServiceError('cancelled', 'Permintaan dibatalkan.')
      return result
    } catch (error) {
      if (version !== generation)
        throw new ServiceError('cancelled', 'Permintaan dibatalkan.')
      if (!(error instanceof ServiceError) || error.status !== 401) throw error
      // Another request may already have renewed the rejected token.
      if (pair?.access_token === sentToken) await refresh()
      try {
        const result = await raw<T>(path, init, pair?.access_token)
        if (version !== generation)
          throw new ServiceError('cancelled', 'Permintaan dibatalkan.')
        return result
      } catch (retryError) {
        if (
          version === generation &&
          retryError instanceof ServiceError &&
          retryError.status === 401
        )
          clear()
        throw retryError
      }
    }
  }
  async function page<T>(
    path: string,
    offset = 0,
    signal?: AbortSignal,
  ): Promise<Page<T>> {
    const items = await authorized<T[]>(`${path}?limit=100&offset=${offset}`, {
      signal,
    })
    return { items, nextOffset: items.length === 100 ? offset + 100 : null }
  }
  function locationId(): string {
    if (!pair?.location_id)
      throw new ServiceError(
        'location_unavailable',
        'Lokasi belum tersedia.',
        404,
      )
    return pair.location_id
  }
  async function inventory(): Promise<DeviceInventory> {
    const id = locationId()
    const locations =
      await authorized<Array<{ id: string; esp_device_id: string | null }>>(
        '/locations',
      )
    const location = locations.find((item) => item.id === id)
    if (!location)
      throw new ServiceError(
        'location_unavailable',
        'Lokasi belum tersedia.',
        404,
      )
    const cameras = await authorized<Array<{ id: string; name: string }>>(
      `/locations/${encodeURIComponent(id)}/cctv`,
    )
    return {
      esp32: location.esp_device_id
        ? { id: location.esp_device_id, name: 'ESP32' }
        : null,
      cameras: cameras.map((camera) => ({
        ...camera,
        configurationState: 'configured',
        verificationState: 'not_tested',
      })),
      selectedDeliveryCameraId: null,
    }
  }
  const installations = new Map<string, string>()
  const unavailable = async (): Promise<never> => {
    throw new ServiceError(
      'integration_unavailable',
      'Fitur belum tersedia.',
      501,
    )
  }
  const service: ApiServices = {
    mode: 'live',
    user: () => pair?.user || null,
    locationId: () => pair?.location_id || null,
    devices: {
      inventory,
      async registerEsp32() {
        const existing = await inventory()
        const data = await authorized<{
          device_id: string
          device_key: string
        }>(`/locations/${encodeURIComponent(locationId())}/esp/credentials`, {
          method: 'POST',
        })
        return {
          inventory: {
            ...existing,
            esp32: { id: data.device_id, name: 'ESP32' },
          },
          credential: data.device_key,
        }
      },
      async registerCamera(input: CameraInput) {
        const connection = input.connection
        if (!connection?.url || !connection.username || !connection.password)
          throw new ServiceError(
            'validation',
            'RTMP URL, username, and password are required.',
            422,
          )
        await authorized(
          `/locations/${encodeURIComponent(locationId())}/cctv`,
          post({
            name: input.name,
            stream_url: connection.url,
            username: connection.username,
            password: connection.password,
          }),
        )
        return inventory()
      },
      renameEsp32: unavailable,
      removeEsp32: unavailable,
      updateCamera: unavailable,
      removeCamera: unavailable,
      selectCamera: unavailable,
    },
    push: {
      async upsert(registration) {
        const previous = installations.get(registration.installationId)
        if (previous && previous !== registration.token)
          await authorized(
            '/notifications/fcm/unregister',
            post({ token: previous }),
          )
        installations.set(registration.installationId, registration.token)
        await authorized(
          '/notifications/fcm',
          post({ location_id: locationId(), token: registration.token }),
        )
      },
      async detach(id) {
        const token = installations.get(id)
        if (!token)
          throw new ServiceError(
            'push_token_missing',
            'Token belum tersedia.',
            409,
          )
        await authorized('/notifications/fcm/unregister', post({ token }))
        installations.delete(id)
      },
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    auth: {
      async login(input) {
        clear()
        const version = generation
        return accept(
          await raw<TokenPair>(
            '/auth/login',
            post({ ...input, email: input.email.trim().toLowerCase() }),
          ),
          version,
        )
      },
      register: (input) =>
        raw(
          '/auth/register',
          post({
            ...input,
            email: input.email.trim().toLowerCase(),
            full_name: input.full_name.trim(),
          }),
        ),
      resend: (input) =>
        raw(
          '/auth/resend-verification',
          post({ ...input, email: input.email.trim().toLowerCase() }),
        ),
      refresh,
      logout: clear,
    },
    shipments: {
      async list(offset, signal) {
        const result = await page<Shipment>('/shipments', offset, signal)
        for (const item of result.items) cache.set(item.id, item)
        return result
      },
      async find(id, signal, reload = false) {
        signal?.throwIfAborted()
        if (reload) cache.delete(id)
        if (cache.has(id)) return cache.get(id)!
        let offset: number | null = 0
        while (offset !== null) {
          signal?.throwIfAborted()
          const result: Page<Shipment> = await service.shipments.list(
            offset,
            signal,
          )
          const match = result.items.find((item) => item.id === id)
          if (match) return match
          offset = result.nextOffset
        }
        return null
      },
      async create(input) {
        const item = await authorized<Shipment>(
          '/shipments',
          post({
            courier: input.courier.trim().toLowerCase(),
            resi_number: input.resi_number.trim().toUpperCase(),
          }),
        )
        cache.set(item.id, item)
        return item
      },
      async refresh(id) {
        const item = await authorized<Shipment>(
          `/shipments/${encodeURIComponent(id)}/refresh`,
          { method: 'POST' },
        )
        cache.set(item.id, item)
        return item
      },
    },
    notifications: {
      list: (offset, signal) =>
        page<PackageNotification>('/notifications', offset, signal),
      connect: (handlers) =>
        connectNotifications(
          service,
          () => pair?.access_token || null,
          () => expiresAt - now(),
          base,
          options.socket,
          handlers,
        ),
    },
    users: {
      list: () => authorized('/auth/users', { cache: 'no-store' }),
      async role(id, role) {
        const user = await authorized<User>(
          `/auth/users/${encodeURIComponent(id)}/role`,
          { method: 'PATCH', body: JSON.stringify({ role }) },
        )
        if (pair?.user.id === id) {
          pair = { ...pair, user }
          notify()
          await refresh()
        }
        return user
      },
    },
  }
  return service
}

function connectNotifications(
  service: ApiServices,
  token: () => string | null,
  lifetime: () => number,
  base: string,
  socketFactory: ClientOptions['socket'],
  handlers: Parameters<ApiServices['notifications']['connect']>[0],
): () => void {
  let disposed = false
  let socket: WebSocket | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  let renewal: ReturnType<typeof setTimeout> | undefined
  let attempts = 0
  let authRetried = false
  let revision = 0
  const seen = new Set<string>()
  const visible = () =>
    typeof document === 'undefined' || document.visibilityState !== 'hidden'
  function stop() {
    revision++
    clearTimeout(timer)
    clearTimeout(renewal)
    if (socket) {
      socket.onclose = null
      socket.onmessage = null
      socket.onerror = null
      socket.close()
      socket = null
    }
  }
  function schedule() {
    if (!disposed && token() && visible())
      timer = setTimeout(
        () => void open(),
        Math.min(1000 * 2 ** attempts++, 30000),
      )
  }
  async function open() {
    stop()
    if (disposed || !token() || !visible()) return
    const version = revision
    try {
      if (lifetime() <= 30000) await service.auth.refresh()
      if (disposed || version !== revision) return
      const url = new URL(
        `${base}/notifications/live`,
        globalThis.location?.href || 'http://localhost',
      )
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      url.searchParams.set('token', token()!)
      socket = socketFactory ? socketFactory(url.href) : new WebSocket(url.href)
      const current = socket
      renewal = setTimeout(
        () => {
          stop()
          void open()
        },
        Math.max(1000, lifetime() - 30000),
      )
      current.onmessage = (event) => {
        if (disposed || version !== revision) return
        try {
          const value = JSON.parse(String(event.data)) as Record<
            string,
            unknown
          >
          if (value.type === 'ready') {
            attempts = 0
            authRetried = false
            handlers.status('connected')
            handlers.ready()
            return
          }
          if (
            typeof value.id !== 'string' ||
            typeof value.shipment_id !== 'string' ||
            typeof value.title !== 'string' ||
            typeof value.message !== 'string' ||
            typeof value.created_at !== 'string' ||
            seen.has(value.id)
          )
            return
          seen.add(value.id)
          if (seen.size > 2000) seen.delete(seen.values().next().value!)
          handlers.event(value as unknown as PackageNotification)
        } catch {
          /* Ignore malformed messages. */
        }
      }
      current.onerror = () => handlers.status('unavailable')
      current.onclose = (event) => {
        clearTimeout(renewal)
        handlers.status('unavailable')
        if (event.code === 4401) {
          if (authRetried) return
          authRetried = true
          void service.auth.refresh().then(schedule).catch(schedule)
        } else schedule()
      }
    } catch {
      if (!disposed && version === revision) {
        handlers.status('unavailable')
        schedule()
      }
    }
  }
  let previousToken = token()
  const unsubscribe = service.subscribe((user) => {
    const next = token()
    if (!user) {
      stop()
      handlers.status('signed-out')
    } else if (next !== previousToken) {
      stop()
      timer = setTimeout(() => void open(), 0)
    }
    previousToken = next
  })
  const visibility = () => {
    stop()
    if (visible()) void open()
    else handlers.status('paused')
  }
  if (typeof document !== 'undefined')
    document.addEventListener('visibilitychange', visibility)
  void open()
  return () => {
    disposed = true
    stop()
    unsubscribe()
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', visibility)
  }
}

// The active application and legacy shipment helper share the same session.
export const liveApi = createApiClient()
