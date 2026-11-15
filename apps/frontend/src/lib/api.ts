// Legacy shipment/feed client, preserved for scaffold compatibility.
// Shipment snapshots cannot establish household ownership or delivery identity.
import { Capacitor } from '@capacitor/core'
import type { PackageNotification, ResiInput, Shipment } from '../types/api'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(
  /\/$/,
  '',
)

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (Capacitor.isNativePlatform() && !/^https:\/\//.test(baseUrl)) {
    throw new Error(
      'Set VITE_API_BASE_URL to an absolute HTTPS API URL for the mobile app.',
    )
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    signal: AbortSignal.timeout(15_000),
  })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? body.detail
        : undefined
    throw new Error(
      typeof detail === 'string'
        ? detail
        : `Request failed (${response.status})`,
    )
  }
  return response.json() as Promise<T>
}

export const api = {
  shipments: () => request<Shipment[]>('/shipments?limit=100'),
  notifications: () =>
    request<PackageNotification[]>('/notifications?limit=100'),
  addShipment: (payload: ResiInput) =>
    request<Shipment>('/shipments', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  refreshShipment: (id: string) =>
    request<Shipment>(`/shipments/${encodeURIComponent(id)}/refresh`, {
      method: 'POST',
    }),
}
