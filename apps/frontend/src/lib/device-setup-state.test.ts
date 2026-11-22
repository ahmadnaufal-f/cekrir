import { describe, expect, it } from 'vitest'
import { isDeviceSetupComplete } from './device-setup-state'
import type { DeviceInventory } from '../types/app'

const empty: DeviceInventory = {
  esp32: null,
  cameras: [],
  selectedDeliveryCameraId: null,
}

describe('saved device setup status', () => {
  it('requires registration for ESP32 without inferring connectivity', () => {
    expect(isDeviceSetupComplete(empty, 'esp32')).toBe(false)
    expect(
      isDeviceSetupComplete(
        { ...empty, esp32: { id: 'esp32-one', name: 'Pintu depan' } },
        'esp32',
      ),
    ).toBe(true)
  })

  it('requires camera configuration and a valid delivery-camera selection', () => {
    const inventory: DeviceInventory = {
      ...empty,
      cameras: [
        {
          id: 'one',
          name: 'Teras',
          configurationState: 'configured',
          verificationState: 'not_tested',
        },
      ],
    }
    expect(isDeviceSetupComplete(empty, 'bardi')).toBe(false)
    expect(isDeviceSetupComplete(inventory, 'bardi')).toBe(false)
    expect(
      isDeviceSetupComplete(
        { ...inventory, selectedDeliveryCameraId: 'missing' },
        'bardi',
      ),
    ).toBe(false)
    expect(
      isDeviceSetupComplete(
        { ...inventory, selectedDeliveryCameraId: 'one' },
        'bardi',
      ),
    ).toBe(true)
  })

  it('keeps incomplete additional cameras visible as unfinished setup', () => {
    const inventory: DeviceInventory = {
      ...empty,
      cameras: [
        {
          id: 'one',
          name: 'Teras',
          configurationState: 'configured',
          verificationState: 'passed',
        },
        {
          id: 'two',
          name: 'Garasi',
          configurationState: 'incomplete',
          verificationState: 'not_tested',
        },
      ],
      selectedDeliveryCameraId: 'one',
    }
    expect(isDeviceSetupComplete(inventory, 'bardi')).toBe(false)
  })

  it('does not equate saved configuration with successful verification', () => {
    expect(
      isDeviceSetupComplete(
        {
          ...empty,
          cameras: [
            {
              id: 'one',
              name: 'Teras',
              configurationState: 'configured',
              verificationState: 'failed',
            },
          ],
          selectedDeliveryCameraId: 'one',
        },
        'bardi',
      ),
    ).toBe(true)
  })
})
