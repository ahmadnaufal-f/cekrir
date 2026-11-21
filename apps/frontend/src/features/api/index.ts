import { liveApi } from './client'
import type { ApiServices } from './contracts'
export async function createShipmentServices(): Promise<ApiServices> {
  if (import.meta.env.DEV && import.meta.env.VITE_APP_MODE === 'mock') {
    const { createApiMock } = await import('./mock')
    return createApiMock()
  }
  return liveApi
}
