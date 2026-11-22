// Compatibility helpers use the active app's session and authenticated transport.
import { liveApi } from '../features/api/client'
export const api = {
  shipments: async () => (await liveApi.shipments.list()).items,
  notifications: async () => (await liveApi.notifications.list()).items,
  addShipment: liveApi.shipments.create,
  refreshShipment: liveApi.shipments.refresh,
}
