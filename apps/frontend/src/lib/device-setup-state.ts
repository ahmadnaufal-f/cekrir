import type { DeviceInventory } from '../types/app'
import type { DeviceCategory } from '../types/device-ui'

/** Saved setup only: this never implies a working hardware connection. */
export function isDeviceSetupComplete(
  inventory: DeviceInventory,
  category: DeviceCategory,
): boolean {
  if (category === 'esp32') return inventory.esp32 !== null
  return (
    inventory.cameras.length > 0 &&
    inventory.cameras.some(
      (camera) => camera.id === inventory.selectedDeliveryCameraId,
    ) &&
    inventory.cameras.every(
      (camera) => camera.configurationState === 'configured',
    )
  )
}
