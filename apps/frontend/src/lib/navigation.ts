import type { AppRoute, AppUser } from '../types/app'

const adminRoutes = new Set([
  '/devices',
  '/devices/setup/esp32',
  '/devices/setup/cameras',
  '/members',
  '/setup',
])
// oxlint-disable-next-line no-control-regex -- Reject control characters in untrusted delivery IDs.
const unsafeDeliveryId = /[\u0000-\u001f/\\?#]/
export function parseRoute(hash: string): AppRoute {
  const value = hash.replace(/^#/, '') || '/deliveries'
  if (
    [
      '/login',
      '/signup',
      '/deliveries',
      '/devices',
      '/devices/setup/esp32',
      '/devices/setup/cameras',
      '/members',
      '/setup',
      '/settings',
    ].includes(value)
  )
    return value as AppRoute
  if (/^\/deliveries\/[^/?#]{1,200}$/.test(value)) {
    try {
      const id = decodeURIComponent(value.slice(12))
      if (id && !unsafeDeliveryId.test(id)) return value as AppRoute
    } catch {
      /* Invalid encoded identifier. */
    }
  }
  return '/deliveries'
}
export function guardRoute(route: AppRoute, user: AppUser | null): AppRoute {
  if (!user) return route === '/signup' ? route : '/login'
  if (route === '/login' || route === '/signup') return '/deliveries'
  if (adminRoutes.has(route) && user.role !== 'admin') return '/deliveries'
  if (route === '/setup') return '/devices'
  return route
}
export function deliveryRoute(id: string): AppRoute {
  return `/deliveries/${encodeURIComponent(id)}`
}
