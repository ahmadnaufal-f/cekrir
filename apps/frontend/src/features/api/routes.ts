export type Route =
  | '/login'
  | '/shipments'
  | `/shipments/${string}`
  | '/notifications'
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
      '/notifications',
      '/members',
      '/settings',
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
