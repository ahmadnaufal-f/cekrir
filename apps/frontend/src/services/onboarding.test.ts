import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLiveServices } from './live'
import { generateEspConfig } from '../lib/esp-firmware'

afterEach(() => {
  vi.unstubAllGlobals()
})

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('live device onboarding', () => {
  it('logs in, provisions the device, and registers and detaches push', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        json({
          access_token: 'access',
          location_id: 'location-1',
          user: {
            id: 'user-1',
            role: 'admin',
            full_name: 'Admin',
            email: 'a@example.test',
          },
        }),
      )
      .mockResolvedValueOnce(
        json([{ id: 'location-1', esp_device_id: 'esp-1' }]),
      )
      .mockResolvedValueOnce(json([{ id: 'camera-1', name: 'Front' }]))
      .mockResolvedValueOnce(
        json({ device_id: 'esp-1', device_key: 'private-key' }),
      )
      .mockResolvedValueOnce(
        json({ device_id: 'push-1', location_id: 'location-1' }),
      )
      .mockResolvedValueOnce(json({ detail: 'Push device removed' }))
    vi.stubGlobal('fetch', fetch)
    const services = createLiveServices()
    const user = await services.auth.login({
      loginId: 'a@example.test',
      password: 'password',
    })
    expect(user.householdId).toBe('location-1')
    const registration = await services.devices.registerEsp32('ESP')
    expect(registration.credential).toBe('private-key')
    expect(registration.inventory.esp32?.id).toBe('esp-1')
    await services.push.upsert({
      installationId: 'install-1',
      platform: 'android',
      token: 'fcm-token',
    })
    await services.push.detach('install-1')
    const call = fetch.mock.calls[4]
    expect(call[0]).toContain('/notifications/fcm')
    expect(JSON.parse(call[1].body)).toEqual({
      location_id: 'location-1',
      token: 'fcm-token',
    })
    expect(call[1].headers.get('Authorization')).toBe('Bearer access')
    expect(fetch.mock.calls[5][0]).toContain('/notifications/fcm/unregister')
  })

  it('generates an HTTPS device config while escaping Wi-Fi credentials', () => {
    const config = generateEspConfig({
      deviceId: 'esp-1',
      deviceKey: 'device-key',
      wifiSsid: 'home"wifi',
      wifiPassword: 'line\nbreak',
      apiBaseUrl: 'https://api.example.test/api/v1',
      rootCa: '-----BEGIN CERTIFICATE-----\nexample',
      courier: 'jne',
    })
    expect(config).toContain('home\\042wifi')
    expect(config).toContain('line\\012break')
    expect(config).toContain('kDeviceKey[] = "device-key"')
    expect(() =>
      generateEspConfig({
        deviceId: 'x',
        deviceKey: 'x',
        wifiSsid: 'x',
        wifiPassword: '',
        apiBaseUrl: 'http://api.example.test/api/v1',
        rootCa: '-----BEGIN CERTIFICATE-----',
        courier: 'jne',
      }),
    ).toThrow('The API URL must be HTTPS and end in /api/v1.')
  })
})
