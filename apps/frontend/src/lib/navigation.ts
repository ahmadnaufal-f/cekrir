import { onUnmounted, shallowRef } from 'vue'
import type { AppRoute, AppUser } from '../types/app'

const adminRoutes = new Set(['/devices', '/members', '/setup'])
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
export function useNavigation() {
  const requested = shallowRef<AppRoute>(parseRoute(window.location.hash))
  const onHash = () => {
    requested.value = parseRoute(window.location.hash)
  }
  window.addEventListener('hashchange', onHash)
  onUnmounted(() => window.removeEventListener('hashchange', onHash))
  function navigate(route: AppRoute, replace = false) {
    requested.value = route
    if (replace) window.history.replaceState(null, '', `#${route}`)
    else if (window.location.hash !== `#${route}`) window.location.hash = route
  }
  return { requested, navigate }
}
