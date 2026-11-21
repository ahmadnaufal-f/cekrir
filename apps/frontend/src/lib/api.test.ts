import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'
import { liveApi } from '../features/api/client'
const user = {
  id: 'user-1',
  email: 'test@example.test',
  full_name: 'Test',
  role: 'member',
  is_active: true,
  created_at: '2026-11-19T00:00:00Z',
}
afterEach(() => {
  liveApi.auth.logout()
  vi.unstubAllGlobals()
})
describe('legacy API compatibility', () => {
  it('requires the active session rather than making unauthenticated requests', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    await expect(api.shipments()).rejects.toMatchObject({ status: 401 })
    expect(fetch).not.toHaveBeenCalled()
  })
  it('submits normalized resi and courier with the active bearer token', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'access',
            refresh_token: 'refresh',
            expires_in: 900,
            refresh_expires_in: 604800,
            user,
          }),
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'shipment-1' })))
    vi.stubGlobal('fetch', fetch)
    await liveApi.auth.login({
      email: 'test@example.test',
      password: 'password',
    })
    await expect(
      api.addShipment({ resi_number: ' ab12345 ', courier: ' JNE ' }),
    ).resolves.toEqual({ id: 'shipment-1' })
    const [url, init] = fetch.mock.calls[1] as [string, RequestInit]
    expect(url).toBe('/api/v1/shipments')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer access')
    expect(JSON.parse(String(init.body))).toEqual({
      resi_number: 'AB12345',
      courier: 'jne',
    })
  })
})
