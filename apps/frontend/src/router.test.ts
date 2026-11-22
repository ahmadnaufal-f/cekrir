import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import type { User } from './features/api/contracts'
import { createAppRouter, signedInRoute } from './router'

function setupRouter(initialRole: User['role'] | null = null) {
  let role = initialRole
  const router = createAppRouter(
    {
      user: () =>
        role && {
          id: 'test-user',
          email: 'user@example.test',
          full_name: 'Test User',
          role,
          is_active: true,
          created_at: '2026-11-19T00:00:00Z',
        },
    },
    createMemoryHistory(),
  )
  return {
    router,
    signIn(nextRole: User['role']) {
      role = nextRole
      return router.replace(
        signedInRoute(router, router.currentRoute.value.query.redirect),
      )
    },
  }
}

describe('application routing', () => {
  it('resumes a saved shipment link after authentication', async () => {
    const { router, signIn } = setupRouter()
    await router.push('/deliveries/parcel%3A123')
    expect(router.currentRoute.value).toMatchObject({
      name: 'login',
      query: { redirect: '/shipments/parcel%3A123' },
    })
    await signIn('member')
    expect(router.currentRoute.value).toMatchObject({
      name: 'shipment-detail',
      params: { id: 'parcel:123' },
    })
  })

  it('resumes a device guide only for admins', async () => {
    const { router, signIn } = setupRouter()
    await router.push('/devices/setup/cameras')
    await signIn('admin')
    expect(router.currentRoute.value.meta.guide).toBe('bardi')
    await router.push({ name: 'esp32-setup' })
    expect(router.currentRoute.value.meta.guide).toBe('esp32')

    const member = setupRouter()
    await member.router.push('/devices/setup/esp32')
    await member.signIn('member')
    expect(member.router.currentRoute.value.name).toBe('shipments')
    await member.router.push('/members')
    expect(member.router.currentRoute.value.name).toBe('shipments')
  })

  it('routes legacy screens and invalid shipment links back to the list', async () => {
    const { router } = setupRouter('member')
    for (const path of [
      '/',
      '/deliveries',
      '/notifications',
      '/shipments/%2fadmin',
      '/shipments/%00',
      '/shipments/bad%20id',
      '/shipments/' + 'a'.repeat(201),
      '/unknown',
    ]) {
      await router.push(path)
      expect(router.currentRoute.value.fullPath).toBe('/shipments')
    }
  })

  it('ignores external or unrelated login return targets', async () => {
    const { router } = setupRouter('member')
    for (const redirect of ['//example.test/shipments/1', '/settings']) {
      await router.push({ name: 'login', query: { redirect } })
      expect(router.currentRoute.value.fullPath).toBe('/shipments')
    }
  })
})
