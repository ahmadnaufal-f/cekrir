import { nextTick, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import type { AppUser, DeliveryPushData, PushRegistration } from '../types/app'
import type { PushService } from '../services/contracts'
import {
  DeliveryIntentCoordinator,
  SimulatedPushBridge,
  createUnavailablePushBridge,
  type PushBridge,
  type PushBridgeListeners,
  type PushPermissionState,
  validateDeliveryPushData,
} from './push'
import { createPushController } from '../composables/usePush'

const householdA = 'household-alpha'
const deliveryIntent: DeliveryPushData = {
  type: 'delivery.created',
  eventId: 'event-001',
  deliveryId: 'delivery-001',
  householdId: householdA,
}

const userA: AppUser = {
  id: 'user-a',
  householdId: householdA,
  role: 'member',
  displayName: 'Ayu',
  loginId: 'ayu@example.test',
}

const userB: AppUser = {
  id: 'user-b',
  householdId: 'household-beta',
  role: 'admin',
  displayName: 'Budi',
  loginId: 'budi@example.test',
}

function makeService(
  upsert: (registration: PushRegistration) => Promise<void> = async () =>
    undefined,
  detach: (installationId: string) => Promise<void> = async () => undefined,
): PushService {
  return {
    upsert: vi.fn(upsert),
    detach: vi.fn(detach),
  }
}

class ControlledPushBridge implements PushBridge {
  readonly kind = 'native' as const
  private listeners: PushBridgeListeners | null = null
  registerCount = 0

  constructor(
    private permissionState: PushPermissionState = 'not-requested',
    private readonly requestedPermission: PushPermissionState = 'granted',
    private readonly tokenOnRegister: string | null = 'test-token-first',
  ) {}

  subscribe(listeners: PushBridgeListeners): () => void {
    this.listeners = listeners
    return () => {
      if (this.listeners === listeners) this.listeners = null
    }
  }

  async permission(): Promise<PushPermissionState> {
    return this.permissionState
  }

  async requestPermission(): Promise<PushPermissionState> {
    this.permissionState = this.requestedPermission
    return this.permissionState
  }

  async register(): Promise<void> {
    this.registerCount += 1
    if (this.tokenOnRegister) this.emitToken(this.tokenOnRegister)
  }

  emitToken(token: string): void {
    this.listeners?.token(token)
  }

  emitTap(payload: unknown): void {
    this.listeners?.tapped(payload)
  }

  dispose(): void {
    this.listeners = null
  }
}

async function settle(): Promise<void> {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
}

describe('validateDeliveryPushData', () => {
  it('accepts only bounded opaque IDs and the exact event type', () => {
    expect(validateDeliveryPushData(deliveryIntent)).toEqual(deliveryIntent)
    expect(
      validateDeliveryPushData({
        data: { ...deliveryIntent, route: '/admin' },
      }),
    ).toEqual(deliveryIntent)
    expect(
      validateDeliveryPushData({ ...deliveryIntent, type: 'delivery.deleted' }),
    ).toBeNull()
    expect(
      validateDeliveryPushData({
        ...deliveryIntent,
        deliveryId: 'https://other.example/path',
      }),
    ).toBeNull()
    expect(
      validateDeliveryPushData({
        ...deliveryIntent,
        eventId: 'e'.repeat(129),
      }),
    ).toBeNull()
    expect(validateDeliveryPushData(null)).toBeNull()
  })
})

describe('DeliveryIntentCoordinator', () => {
  it('retains an early tap until both authentication and navigation are ready', async () => {
    const navigate = vi.fn(() => true)
    const coordinator = new DeliveryIntentCoordinator({ navigate })

    expect(coordinator.acceptTap(deliveryIntent)).toEqual(deliveryIntent)
    expect(coordinator.pending).toEqual([deliveryIntent])

    coordinator.setContext({
      userId: 'user-a',
      householdId: householdA,
      navigationReady: false,
    })
    await settle()
    expect(navigate).not.toHaveBeenCalled()

    coordinator.setContext({
      userId: 'user-a',
      householdId: householdA,
      navigationReady: true,
    })
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledTimes(1))
    expect(navigate).toHaveBeenCalledWith(deliveryIntent.deliveryId)
    expect(coordinator.pending).toEqual([])
    expect(coordinator.acceptTap(deliveryIntent)).toBeNull()
  })

  it('dedupes foreground receives independently from a single tap navigation', async () => {
    const navigate = vi.fn(() => true)
    const coordinator = new DeliveryIntentCoordinator({ navigate })

    expect(coordinator.acceptReceived(deliveryIntent)).toEqual(deliveryIntent)
    expect(coordinator.acceptReceived(deliveryIntent)).toBeNull()
    expect(coordinator.acceptTap(deliveryIntent)).toEqual(deliveryIntent)
    expect(coordinator.acceptTap(deliveryIntent)).toBeNull()

    coordinator.setContext({
      userId: 'user-a',
      householdId: householdA,
      navigationReady: true,
    })
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledTimes(1))
  })

  it('rejects a different-household intent without passing it to navigation', async () => {
    const navigate = vi.fn(() => true)
    const onOutcome = vi.fn()
    const coordinator = new DeliveryIntentCoordinator({ navigate, onOutcome })

    coordinator.acceptTap({ ...deliveryIntent, householdId: 'household-beta' })
    coordinator.setContext({
      userId: 'user-a',
      householdId: householdA,
      navigationReady: true,
    })
    await settle()

    expect(navigate).not.toHaveBeenCalled()
    expect(coordinator.pending).toEqual([])
    expect(onOutcome).toHaveBeenCalledWith(
      { ...deliveryIntent, householdId: 'household-beta' },
      'rejected',
    )
  })

  it('keeps a route failure pending until an explicit retry is accepted', async () => {
    const navigate = vi
      .fn<(_: string) => Promise<boolean>>()
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(true)
    const onRouteError = vi.fn()
    const coordinator = new DeliveryIntentCoordinator({
      navigate,
      onRouteError,
    })

    coordinator.setContext({
      userId: 'user-a',
      householdId: householdA,
      navigationReady: true,
    })
    coordinator.acceptTap(deliveryIntent)
    await vi.waitFor(() => expect(onRouteError).toHaveBeenCalledTimes(1))
    expect(coordinator.pending).toEqual([deliveryIntent])

    expect(coordinator.retryPending(deliveryIntent.eventId)).toBe(true)
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledTimes(2))
    expect(coordinator.pending).toEqual([])
  })
})

describe('push controller lifecycle', () => {
  it('holds a cold-start tap across auth restoration and waits for the router', async () => {
    const bridge = new SimulatedPushBridge()
    const user = ref<AppUser | null>(null)
    const navigationReady = ref(false)
    const onNavigate = vi.fn(() => true)
    const controller = createPushController({
      bridge,
      service: makeService(),
      user,
      navigationReady,
      onNavigate,
      onRefresh: vi.fn(),
    })

    bridge.simulateTap(deliveryIntent)
    expect(controller.state.value.pendingNavigation).toBe(true)
    user.value = userA
    await settle()
    expect(onNavigate).not.toHaveBeenCalled()

    navigationReady.value = true
    await vi.waitFor(() => expect(onNavigate).toHaveBeenCalledTimes(1))
    expect(onNavigate).toHaveBeenCalledWith(deliveryIntent.deliveryId)
    controller.dispose()
  })

  it('refreshes and banners one received event while allowing one navigation tap', async () => {
    const bridge = new SimulatedPushBridge()
    const refresh = vi.fn()
    const navigate = vi.fn(() => true)
    const controller = createPushController({
      bridge,
      service: makeService(),
      user: ref<AppUser | null>(userA),
      navigationReady: ref(true),
      onNavigate: navigate,
      onRefresh: refresh,
    })

    bridge.simulateReceived(deliveryIntent)
    bridge.simulateReceived(deliveryIntent)
    await settle()
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(controller.state.value.banner).toEqual({
      eventId: deliveryIntent.eventId,
      deliveryId: deliveryIntent.deliveryId,
    })

    bridge.simulateTap(deliveryIntent)
    bridge.simulateTap(deliveryIntent)
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledTimes(1))
    expect(controller.state.value.banner).toBeNull()
    controller.dispose()
  })

  it('does not refresh or show a foreground event from another household', async () => {
    const bridge = new SimulatedPushBridge()
    const refresh = vi.fn()
    const controller = createPushController({
      bridge,
      service: makeService(),
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: refresh,
    })

    bridge.simulateReceived({
      ...deliveryIntent,
      householdId: userB.householdId,
    })
    await settle()
    expect(refresh).not.toHaveBeenCalled()
    expect(controller.state.value.banner).toBeNull()
    controller.dispose()
  })

  it('blocks reassociation after auth expiry until detach is explicitly retried', async () => {
    let finishFirstUpsert: (() => void) | undefined
    const firstUpsert = new Promise<void>((resolve) => {
      finishFirstUpsert = resolve
    })
    const order: string[] = []
    let upsertCount = 0
    const service = makeService(
      async () => {
        upsertCount += 1
        order.push(`upsert-${upsertCount}`)
        if (upsertCount === 1) await firstUpsert
      },
      async () => {
        order.push('detach')
      },
    )
    const bridge = new SimulatedPushBridge()
    const user = ref<AppUser | null>(userA)
    const controller = createPushController({
      bridge,
      service,
      user,
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    const enable = controller.enable()
    await vi.waitFor(() => expect(service.upsert).toHaveBeenCalledTimes(1))
    user.value = null
    user.value = userB
    finishFirstUpsert?.()
    await enable
    await settle()

    expect(controller.state.value.association).toBe('blocked')
    expect(service.upsert).toHaveBeenCalledTimes(1)

    await controller.retry()
    expect(order).toEqual(['upsert-1', 'detach', 'upsert-2'])
    controller.dispose()
  })

  it('detaches after an ambiguous failed upsert before logout can proceed', async () => {
    const service = makeService(async () => {
      throw new Error('response was lost')
    })
    const bridge = new SimulatedPushBridge()
    const controller = createPushController({
      bridge,
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    await controller.enable()
    expect(controller.state.value.association).toBe('failed')
    await expect(controller.beforeLogout()).resolves.toBe(true)
    expect(service.detach).toHaveBeenCalledTimes(1)
    controller.dispose()
  })

  it('keeps a failed detach blocked and requires an explicit retry', async () => {
    let detachCount = 0
    const service = makeService(
      async () => undefined,
      async () => {
        detachCount += 1
        if (detachCount === 1) throw new Error('offline')
      },
    )
    const bridge = new SimulatedPushBridge()
    const controller = createPushController({
      bridge,
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    await controller.enable()
    await expect(controller.beforeLogout()).resolves.toBe(false)
    expect(controller.state.value.association).toBe('blocked')
    await controller.retry()
    expect(service.detach).toHaveBeenCalledTimes(2)
    expect(controller.state.value.association).toBe('registered')
    controller.dispose()
  })

  it('does not fabricate browser permission or use simulation in the unavailable bridge', async () => {
    const service = makeService()
    const controller = createPushController({
      bridge: createUnavailablePushBridge(),
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    await controller.enable()
    controller.simulateReceived(deliveryIntent)
    controller.simulateTap(deliveryIntent)
    expect(controller.state.value.mode).toBe('unavailable')
    expect(controller.state.value.permission).toBe('unsupported')
    expect(service.upsert).not.toHaveBeenCalled()
    controller.dispose()
  })

  it('keeps deliveries usable when notification permission is denied', async () => {
    const bridge = new ControlledPushBridge('not-requested', 'denied')
    const service = makeService()
    const navigate = vi.fn(() => true)
    const controller = createPushController({
      bridge,
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: navigate,
      onRefresh: vi.fn(),
    })

    await controller.enable()

    expect(controller.state.value.permission).toBe('denied')
    expect(controller.state.value.association).toBe('idle')
    expect(bridge.registerCount).toBe(0)
    expect(service.upsert).not.toHaveBeenCalled()
    controller.setNavigationReady(true)
    bridge.emitTap(deliveryIntent)
    await vi.waitFor(() =>
      expect(navigate).toHaveBeenCalledWith(deliveryIntent.deliveryId),
    )
    expect(await controller.beforeLogout()).toBe(true)
    controller.dispose()
  })

  it('upserts a refreshed token for the current account', async () => {
    const seenTokens: string[] = []
    const service = makeService(async ({ token }) => {
      seenTokens.push(token)
    })
    const bridge = new ControlledPushBridge()
    const controller = createPushController({
      bridge,
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    await controller.enable()
    expect(seenTokens).toEqual(['test-token-first'])
    expect(controller.state.value.association).toBe('registered')

    bridge.emitToken('test-token-refreshed')
    await vi.waitFor(() =>
      expect(seenTokens).toEqual(['test-token-first', 'test-token-refreshed']),
    )
    expect(controller.state.value.association).toBe('registered')
    controller.dispose()
  })

  it('does not mark a refreshed token registered when only the old upsert completes', async () => {
    let finishFirstUpsert: (() => void) | undefined
    let finishSecondUpsert: (() => void) | undefined
    const firstUpsert = new Promise<void>((resolve) => {
      finishFirstUpsert = resolve
    })
    const secondUpsert = new Promise<void>((resolve) => {
      finishSecondUpsert = resolve
    })
    const seenTokens: string[] = []
    const service = makeService(async ({ token }) => {
      seenTokens.push(token)
      await (token === 'test-token-first' ? firstUpsert : secondUpsert)
    })
    const bridge = new ControlledPushBridge()
    const controller = createPushController({
      bridge,
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    const enabling = controller.enable()
    await vi.waitFor(() => expect(seenTokens).toEqual(['test-token-first']))
    bridge.emitToken('test-token-refreshed')
    expect(controller.state.value.association).toBe('pending')

    finishFirstUpsert?.()
    await vi.waitFor(() =>
      expect(seenTokens).toEqual(['test-token-first', 'test-token-refreshed']),
    )
    expect(controller.state.value.association).toBe('pending')

    finishSecondUpsert?.()
    await vi.waitFor(() =>
      expect(controller.state.value.association).toBe('registered'),
    )
    await enabling
    controller.dispose()
  })

  it('keeps granted permission separate from a failed backend association', async () => {
    const service = makeService(async () => {
      throw new Error('association unavailable')
    })
    const controller = createPushController({
      bridge: new ControlledPushBridge(),
      service,
      user: ref<AppUser | null>(userA),
      onNavigate: vi.fn(() => true),
      onRefresh: vi.fn(),
    })

    await controller.enable()

    expect(controller.state.value.permission).toBe('granted')
    expect(controller.state.value.association).toBe('failed')
    expect(service.upsert).toHaveBeenCalledTimes(1)
    controller.dispose()
  })
})
