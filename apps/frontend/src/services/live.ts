import { Capacitor } from '@capacitor/core'
import {
  ServiceError,
  type AppServices,
  type CredentialStore,
} from './contracts'
import { serviceCopy as copy } from '../lib/service-copy'

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
    if (Capacitor.isNativePlatform() && !/^https:\/\//.test(base))
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
  const unavailable = async (): Promise<never> => {
    throw new ServiceError('integration_unavailable', copy.unavailable, 501)
  }
  return {
    mode: 'live',
    auth: {
      restore: async () => null,
      login: unavailable,
      signup: unavailable,
      logout: async () => {},
    },
    deliveries: { list: unavailable, detail: unavailable, photo: unavailable },
    devices: {
      inventory: unavailable,
      registerEsp32: unavailable,
      registerCamera: unavailable,
      selectCamera: unavailable,
    },
    members: { list: unavailable, create: unavailable },
    setup: { content: unavailable },
    push: { upsert: unavailable, detach: unavailable },
  }
}
