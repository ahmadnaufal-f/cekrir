import { createLiveServices } from './live'
import type { AppServices } from './contracts'

export async function createServices(): Promise<AppServices> {
  if (import.meta.env.DEV && import.meta.env.VITE_APP_MODE === 'mock') {
    const { createMockServices } = await import('./mock')
    return createMockServices()
  }
  return createLiveServices()
}
