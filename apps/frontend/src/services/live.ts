import { Capacitor } from '@capacitor/core'
import {
  ServiceError,
  type AppServices,
  type CredentialStore,
} from './contracts'
import { serviceCopy as copy } from '../lib/service-copy'
import type {
  AppUser,
  CameraInput,
  DeviceInventory,
  PushRegistration,
} from '../types/app'

export function createMemoryCredentialStore(): CredentialStore {
  let value: string | null = null
  return {
    read: () => value,
    write: (next) => {
      value = next
    },
    clear: () => {
      value = null
    },
  }
}

// This transport is ready for an agreed bearer contract. No proposed endpoints
// are enabled merely because they appeared in a design document.
export function createAuthorizedTransport(
  baseUrl: string,
  credentials: CredentialStore,
  onUnauthorized: () => void = () => {},
) {
  const base = baseUrl.replace(/\/+$/, '')
  let retryAt = 0
  return async function request<T>(
    path: string,
    init: RequestInit = {},
    binary = false,
  ): Promise<T> {
    if (Date.now() < retryAt)
      throw new ServiceError(
        'rate_limited',
        copy.http[429],
        429,
        {},
        String(Math.ceil((retryAt - Date.now()) / 1000)),
      )
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('://'))
      throw new ServiceError('invalid_path', copy.invalidPath)
    if (Capacitor.isNativePlatform() && !base.startsWith('https://'))
      throw new ServiceError('configuration', copy.nativeHttps)
    const token = credentials.read()
    const headers = new Headers(init.headers)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    if (init.body) headers.set('Content-Type', 'application/json')
    let response: Response
    try {
      response = await fetch(`${base}${path}`, {
        ...init,
        headers,
        signal: init.signal
          ? AbortSignal.any([init.signal, AbortSignal.timeout(15000)])
          : AbortSignal.timeout(15000),
      })
    } catch {
      throw new ServiceError('connection', copy.connection)
    }
    if (!response.ok) {
      if (response.status === 401) {
        credentials.clear()
        onUnauthorized()
      }
      const body: unknown = await response.json().catch(() => null)
      const data =
        body && typeof body === 'object'
          ? (body as Record<string, unknown>)
          : {}
      const retryAfter = response.headers.get('Retry-After') || undefined
      if (response.status === 429 && retryAfter) {
        const delay = /^\d+$/.test(retryAfter)
          ? Number(retryAfter) * 1000
          : Date.parse(retryAfter) - Date.now()
        if (Number.isFinite(delay) && delay > 0) retryAt = Date.now() + delay
      }
      const fields: Record<string, string> = {}
      if (data.fieldErrors && typeof data.fieldErrors === 'object')
        for (const [key, value] of Object.entries(data.fieldErrors))
          if (typeof value === 'string') fields[key] = value
      throw new ServiceError(
        typeof data.code === 'string' ? data.code : 'request_failed',
        copy.http[response.status] || copy.failed,
        response.status,
        fields,
        retryAfter,
      )
    }
    if (binary) return (await response.blob()) as T
    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }
}

export function createLiveServices(): AppServices {
  const credentials = createMemoryCredentialStore()
  const request = createAuthorizedTransport(
    import.meta.env.VITE_API_BASE_URL || '/api/v1',
    credentials,
    () => {
      currentUser = null
    },
  )
  let currentUser: AppUser | null = null
  const installations = new Map<string, string>()
  const unavailable = async (): Promise<never> => {
    throw new ServiceError('integration_unavailable', copy.unavailable, 501)
  }
  function locationId(): string {
    if (!currentUser?.householdId)
      throw new ServiceError('location_unavailable', copy.unavailable, 404)
    return currentUser.householdId
  }
  async function inventory(): Promise<DeviceInventory> {
    const id = locationId()
    const locations =
      await request<Array<{ id: string; esp_device_id: string | null }>>(
        '/locations',
      )
    const location = locations.find((entry) => entry.id === id)
    if (!location)
      throw new ServiceError('location_unavailable', copy.unavailable, 404)
    const cameras = await request<Array<{ id: string; name: string }>>(
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
  async function login(input: {
    loginId: string
    password: string
  }): Promise<AppUser> {
    const result = await request<{
      access_token: string
      location_id: string | null
      user: {
        id: string
        email: string
        full_name: string
        role: 'admin' | 'member'
      }
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: input.loginId, password: input.password }),
    })
    credentials.write(result.access_token)
    currentUser = {
      id: result.user.id,
      householdId: result.location_id ?? '',
      role: result.user.role,
      displayName: result.user.full_name,
      loginId: result.user.email,
    }
    return currentUser
  }
  async function registerCamera(input: CameraInput): Promise<DeviceInventory> {
    const connection = input.connection
    if (!connection?.url || !connection.username || !connection.password)
      throw new ServiceError(
        'validation',
        'RTMP URL, username, and password are required.',
        422,
      )
    await request(`/locations/${encodeURIComponent(locationId())}/cctv`, {
      method: 'POST',
      body: JSON.stringify({
        name: input.name,
        stream_url: connection.url,
        username: connection.username,
        password: connection.password,
      }),
    })
    return inventory()
  }
  async function registerPush(registration: PushRegistration): Promise<void> {
    const previous = installations.get(registration.installationId)
    if (previous && previous !== registration.token) {
      await request('/notifications/fcm/unregister', {
        method: 'POST',
        body: JSON.stringify({ token: previous }),
      })
    }
    installations.set(registration.installationId, registration.token)
    await request('/notifications/fcm', {
      method: 'POST',
      body: JSON.stringify({
        location_id: locationId(),
        token: registration.token,
      }),
    })
  }
  async function detachPush(installationId: string): Promise<void> {
    const token = installations.get(installationId)
    if (!token)
      throw new ServiceError('push_token_missing', copy.unavailable, 409)
    await request('/notifications/fcm/unregister', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    installations.delete(installationId)
  }
  return {
    mode: 'live',
    auth: {
      restore: async () => currentUser,
      login,
      signup: unavailable,
      logout: async () => {
        credentials.clear()
        currentUser = null
      },
    },
    deliveries: {
      totals: unavailable,
      list: unavailable,
      detail: unavailable,
      photo: unavailable,
    },
    devices: {
      inventory,
      registerEsp32: async () => {
        const existing = await inventory()
        const data = await request<{ device_id: string; device_key: string }>(
          `/locations/${encodeURIComponent(locationId())}/esp/credentials`,
          { method: 'POST' },
        )
        return {
          inventory: {
            ...existing,
            esp32: { id: data.device_id, name: 'ESP32' },
          },
          credential: data.device_key,
        }
      },
      registerCamera,
      renameEsp32: unavailable,
      removeEsp32: unavailable,
      updateCamera: unavailable,
      removeCamera: unavailable,
      selectCamera: unavailable,
    },
    members: { list: unavailable, create: unavailable },
    setup: { content: unavailable },
    push: { upsert: registerPush, detach: detachPush },
  }
}
