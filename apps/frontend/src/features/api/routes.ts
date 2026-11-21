export const deviceGuideRoutes = {
  esp32: '/devices/setup/esp32',
  bardi: '/devices/setup/cameras',
} as const

export type Route =
  | '/login'
  | '/shipments'
  | `/shipments/${string}`
  | '/devices'
  | (typeof deviceGuideRoutes)[keyof typeof deviceGuideRoutes]
  | '/members'
  | '/settings'
// oxlint-disable-next-line no-control-regex -- Reject control characters in identifiers.
const unsafeId = /[\s/\\?#\u0000-\u001f]/
export function parseApiRoute(hash: string): Route {
  const raw = hash
    .replace(/^#/, '')
    .replace(/^\/deliveries(?=\/|$)/, '/shipments')
  if (
    [
      '/login',
      '/shipments',
      '/devices',
      '/members',
      '/settings',
      ...Object.values(deviceGuideRoutes),
    ].includes(raw)
  )
    return raw as Route
  if (/^\/shipments\/[^/?#]{1,200}$/.test(raw)) {
    try {
      if (!unsafeId.test(decodeURIComponent(raw.slice(11)))) return raw as Route
    } catch {
      /* Invalid identifier. */
    }
  }
  return '/shipments'
}
export const shipmentRoute = (id: string): Route =>
  `/shipments/${encodeURIComponent(id)}`
