import { describe, expect, it } from 'vitest'
import { deliveryRoute, guardRoute, parseRoute } from './navigation'
import type { AppUser } from '../types/app'

const admin: AppUser = {
  id: 'account-admin',
  householdId: 'household-one',
  role: 'admin',
  displayName: 'Admin',
  loginId: 'admin@example.test',
}

const member: AppUser = {
  id: 'account-member',
  householdId: 'household-one',
  role: 'member',
  displayName: 'Member',
  loginId: 'member@example.test',
}

describe('navigation', () => {
  it.each([
    '/devices',
    '/devices/setup/esp32',
    '/devices/setup/cameras',
    '/members',
    '/setup',
  ] as const)(
    'blocks a member opening the admin route %s directly',
    (route) => {
      expect(guardRoute(route, member)).toBe('/deliveries')
    },
  )

  it('allows admins to open management routes directly', () => {
    expect(guardRoute('/devices', admin)).toBe('/devices')
    expect(guardRoute('/members', admin)).toBe('/members')
    expect(guardRoute('/setup', admin)).toBe('/devices')
    expect(guardRoute('/devices/setup/esp32', admin)).toBe(
      '/devices/setup/esp32',
    )
    expect(guardRoute('/devices/setup/cameras', admin)).toBe(
      '/devices/setup/cameras',
    )
  })

  it('sends signed-out users to login except for signup', () => {
    expect(guardRoute('/devices', null)).toBe('/login')
    expect(guardRoute('/signup', null)).toBe('/signup')
    expect(guardRoute('/devices/setup/esp32', null)).toBe('/login')
    expect(guardRoute('/devices/setup/cameras', null)).toBe('/login')
  })

  it.each(['/devices/setup/esp32', '/devices/setup/cameras'] as const)(
    'parses the category-specific setup page %s',
    (route) => {
      expect(parseRoute(`#${route}`)).toBe(route)
    },
  )

  it('redirects authenticated users away from login and signup', () => {
    expect(guardRoute('/login', admin)).toBe('/deliveries')
    expect(guardRoute('/signup', member)).toBe('/deliveries')
  })

  it('round-trips an opaque non-UUID delivery ID', () => {
    const route = deliveryRoute('spx:2026.label_09')

    expect(route).toBe('/deliveries/spx%3A2026.label_09')
    expect(parseRoute(`#${route}`)).toBe(route)
  })

  it.each([
    '/deliveries/%',
    '/deliveries/%2Fprivate',
    '/deliveries/%5Cprivate',
    '/deliveries/%3Fquery',
    '/deliveries/%00',
    '/deliveries/id/extra',
    '/unknown',
  ])('falls back safely for invalid or arbitrary route %s', (route) => {
    expect(parseRoute(route)).toBe('/deliveries')
  })
})
