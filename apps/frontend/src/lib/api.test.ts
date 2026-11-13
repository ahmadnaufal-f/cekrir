import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

describe('API boundary', () => {
  it('submits the resi and courier to the backend', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: 'shipment-1' })))
    vi.stubGlobal('fetch', fetch)
    await expect(
      api.addShipment({ resi_number: 'AB12345', courier: 'jne' }),
    ).resolves.toEqual({
      id: 'shipment-1',
    })
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/shipments',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ resi_number: 'AB12345', courier: 'jne' }),
      }),
    )
  })

  it('makes tracking failures actionable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Provider unavailable' }), {
          status: 502,
        }),
      ),
    )
    await expect(api.shipments()).rejects.toThrow('Provider unavailable')
  })

  it('handles non-JSON proxy errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('Bad gateway', { status: 502 })),
    )
    await expect(api.shipments()).rejects.toThrow('Request failed (502)')
  })
})
