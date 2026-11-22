import { afterEach, describe, expect, it, vi } from 'vitest'

const plugin = vi.hoisted(() => ({
  addListener: vi.fn(), checkPermissions: vi.fn(), requestPermissions: vi.fn(), register: vi.fn(),
}))
vi.mock('@capacitor/push-notifications', () => ({ PushNotifications: plugin }))

import { AndroidPushBridge } from './push'

afterEach(() => vi.resetAllMocks())

describe('Android push bridge', () => {
  it('asks permission, receives registration and push events, and removes its listeners', async () => {
    const callbacks = new Map<string, (value: unknown) => void>()
    const remove = vi.fn().mockResolvedValue(undefined)
    plugin.addListener.mockImplementation(async (name: string, listener: (value: unknown) => void) => {
      callbacks.set(name, listener)
      return { remove }
    })
    plugin.requestPermissions.mockResolvedValue({ receive: 'granted' })
    plugin.register.mockResolvedValue(undefined)
    const bridge = new AndroidPushBridge()
    const listeners = { token: vi.fn(), received: vi.fn(), tapped: vi.fn(), error: vi.fn() }
    bridge.subscribe(listeners)
    expect(await bridge.requestPermission()).toBe('granted')
    await bridge.register()
    callbacks.get('registration')?.({ value: 'fcm-token' })
    callbacks.get('pushNotificationReceived')?.({ data: { type: 'delivery.created' } })
    expect(listeners.token).toHaveBeenCalledWith('fcm-token')
    expect(listeners.received).toHaveBeenCalledOnce()
    await bridge.dispose()
    expect(remove).toHaveBeenCalledTimes(4)
  })
})
