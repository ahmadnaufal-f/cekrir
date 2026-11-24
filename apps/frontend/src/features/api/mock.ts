import { createApiClient } from './client'
import type {
  ApiServices,
  PackageNotification,
  Shipment,
  User,
} from './contracts'
import { createMockServices } from '../../services/mock'

export function createApiMock({ simulateDetection = false } = {}): ApiServices {
  const date = '2026-11-19T08:00:00Z'
  const users: User[] = ['admin', 'member'].map((role, index) => ({
    id: `demo-user-${index}`,
    email: `${role}@demo.test`,
    full_name: role === 'admin' ? 'Admin Demo' : 'Anggota Demo',
    role: role as User['role'],
    is_active: true,
    created_at: date,
  }))
  const demoShipment: Shipment = {
    id: 'demo-shipment-1',
    courier: 'jne',
    resi_number: 'DEMO123456',
    status: 'in_transit',
    summary: 'Paket simulasi sedang dikirim.',
    provider: 'demo',
    source: 'camera',
    camera_id: 'demo-camera',
    created_at: date,
    checked_at: date,
    last_detected_at: date,
    history: [
      {
        occurred_at: date,
        description: 'Diterima di pusat sortir',
        location: 'Jakarta',
      },
    ],
  }
  const shipments = [demoShipment]
  const notifications: PackageNotification[] = [
    {
      id: 'demo-notification',
      shipment_id: demoShipment.id,
      title: 'Paket terdeteksi',
      message: 'Notifikasi simulasi dalam aplikasi.',
      created_at: date,
    },
  ]
  let detectionPending = simulateDetection
  const pending = new Set<string>()
  const client = createApiClient({
    baseUrl: 'https://demo.invalid/api/v1',
    fetch: async (input, init) => {
      const url = new URL(String(input))
      const path = url.pathname.replace('/api/v1', '')
      const body = typeof init?.body === 'string' ? JSON.parse(init.body) : {}
      const response = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), {
          status,
          headers: { 'Content-Type': 'application/json' },
        })
      const token = new Headers(init?.headers)
        .get('Authorization')
        ?.replace('Bearer ', '')
      const user = users.find((value) => value.id === token)
      const pair = (value: User) => ({
        access_token: value.id,
        refresh_token: value.id,
        expires_in: 900,
        refresh_expires_in: 604800,
        user: value,
      })
      if (path === '/auth/register') {
        if (
          users.some((value) => value.email === body.email) ||
          pending.has(body.email)
        )
          return response({ detail: 'Email is already registered' }, 409)
        pending.add(body.email)
        return response(
          { detail: 'Check your email for a verification link.' },
          201,
        )
      }
      if (path === '/auth/resend-verification')
        return response({ detail: 'Check your email for a verification link.' })
      if (path === '/auth/login') {
        const match = users.find((value) => value.email === body.email)
        return match && body.password === 'demo12345678'
          ? response(pair(match))
          : response({}, 401)
      }
      if (path === '/auth/refresh') {
        const match = users.find((value) => value.id === body.refresh_token)
        return match ? response(pair(match)) : response({}, 401)
      }
      if (!user) return response({}, 401)
      if (path === '/shipments/analyze-screenshot' && init?.method === 'POST')
        return response({
          resi_number: '000Demo123',
          courier_service: 'SPX Express',
          sender_name: 'Toko Contoh',
          product_names: ['Kotak penyimpanan'],
        })
      if (path === '/shipments' && init?.method === 'POST') {
        const existing = shipments.find(
          (value) =>
            value.courier === body.courier &&
            value.resi_number === body.resi_number,
        )
        if (existing) return response(existing)
        const value: Shipment = {
          ...demoShipment,
          ...body,
          id: `demo-shipment-${shipments.length + 1}`,
          source: 'manual',
          camera_id: null,
          last_detected_at: null,
          history: [],
          created_at: new Date().toISOString(),
        }
        shipments.unshift(value)
        return response(value, 201)
      }
      if (path === '/shipments')
        return response(
          shipments.slice(
            Number(url.searchParams.get('offset')),
            Number(url.searchParams.get('offset')) + 100,
          ),
        )
      if (path.startsWith('/shipments/') && path.endsWith('/refresh')) {
        if (user.role !== 'admin') return response({}, 403)
        const item = shipments.find((value) => value.id === path.split('/')[2])
        if (!item) return response({}, 404)
        item.checked_at = new Date().toISOString()
        return response(item)
      }
      if (path === '/notifications')
        return response(
          Number(url.searchParams.get('offset')) ? [] : notifications,
        )
      if (user.role !== 'admin') return response({}, 403)
      if (path === '/auth/users') return response(users)
      if (path.endsWith('/role')) {
        const target = users.find((value) => value.id === path.split('/')[3])
        if (!target) return response({}, 404)
        target.role = body.role
        return response(target)
      }
      return response({}, 404)
    },
  })
  const { devices } = createMockServices({
    deviceUser() {
      const user = client.user()
      return (
        user && {
          id: user.id,
          role: user.role,
          displayName: user.full_name,
          loginId: user.email,
          householdId: 'household-demo',
        }
      )
    },
  })
  return {
    ...client,
    mode: 'mock',
    devices,
    notifications: {
      ...client.notifications,
      connect(handlers) {
        handlers.status('demo')
        if (!detectionPending) return () => {}

        const timer = setTimeout(() => {
          if (!detectionPending || !client.user()) return
          detectionPending = false

          const now = new Date().toISOString()
          const shipment: Shipment = {
            ...demoShipment,
            id: 'demo-detected-shipment',
            resi_number: 'DEMO-NEW-001',
            summary: 'Paket baru terdeteksi oleh kamera simulasi.',
            created_at: now,
            checked_at: now,
            last_detected_at: now,
            history: [],
          }
          const notification: PackageNotification = {
            id: 'demo-detection',
            shipment_id: shipment.id,
            title: 'Paket terdeteksi',
            message: `Paket dengan resi ${shipment.resi_number} terdeteksi.`,
            created_at: now,
          }
          shipments.unshift(shipment)
          notifications.unshift(notification)
          handlers.event(notification)
        }, 1000)
        return () => clearTimeout(timer)
      },
    },
  }
}
