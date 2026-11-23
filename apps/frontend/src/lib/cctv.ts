import type { CameraSummary, DeviceInventory } from '../types/app'

export interface CctvRecord {
  id: string
  name: string
  tuya_device_id?: string | null
  is_delivery_camera?: boolean
}

export function cameraInventory(cameras: CctvRecord[]) {
  return {
    cameras: cameras.map((camera): CameraSummary => ({
      id: camera.id,
      name: camera.name,
      tuyaDeviceId: camera.tuya_device_id,
      configurationState: 'configured',
      verificationState: 'not_tested',
    })),
    selectedDeliveryCameraId:
      cameras.find((camera) => camera.is_delivery_camera)?.id ?? null,
  } satisfies Pick<DeviceInventory, 'cameras' | 'selectedDeliveryCameraId'>
}
