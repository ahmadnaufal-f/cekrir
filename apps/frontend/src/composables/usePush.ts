import { readonly, shallowRef, watch, type Ref } from 'vue'
import type { AppUser, DeliveryPushData, PushRegistration } from '../types/app'
import type { PushService } from '../services/contracts'
import {
  DeliveryIntentCoordinator,
  type PushBridge,
  type PushBridgeKind,
  type PushPermissionState,
  type PushSimulator,
  validateDeliveryPushData,
} from '../lib/push'
import { pushCopy } from '../lib/push-copy'

export type PushAssociationState =
  'idle' | 'pending' | 'registered' | 'failed' | 'blocked'

export interface PushBanner {
  eventId: string
  deliveryId: string
}

export interface PushState {
  mode: PushBridgeKind
  permission: PushPermissionState
  association: PushAssociationState
  busy: boolean
  error: string | null
  banner: PushBanner | null
  pendingNavigation: boolean
}

export interface UsePushOptions {
  bridge: PushBridge
  service: PushService
  user: Readonly<Ref<AppUser | null>>
  onNavigate(deliveryId: string): boolean | Promise<boolean>
  onRefresh(): void | Promise<void>
  navigationReady?: Readonly<Ref<boolean>>
}

export interface PushController {
  state: Readonly<Ref<PushState>>
  enable(): Promise<void>
  retry(): Promise<void>
  simulateReceived(payload: unknown): void
  simulateTap(payload: unknown): void
  tapBanner(): void
  dismissBanner(): void
  setNavigationReady(ready: boolean): void
  beforeLogout(): Promise<boolean>
  dispose(): void
}

interface AssociationAttempt {
  userId: string
  token: string
  promise: Promise<void>
}

// No approved persistent installation store exists in this prototype. Keep the
// nonsecret identity in memory only; a page/process restart creates a new one.
let memoryInstallationId: string | null = null

function installationId(): string {
  if (memoryInstallationId) return memoryInstallationId

  const randomUuid = globalThis.crypto?.randomUUID?.()
  memoryInstallationId = randomUuid
    ? `web-${randomUuid}`
    : `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  return memoryInstallationId
}

function validToken(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= 4096
}

export function createPushController(options: UsePushOptions): PushController {
  const mutableState = shallowRef<PushState>({
    mode:
      options.bridge.kind === 'simulated' && !import.meta.env.DEV
        ? 'unavailable'
        : options.bridge.kind,
    permission: 'not-requested',
    association: 'idle',
    busy: false,
    error: null,
    banner: null,
    pendingNavigation: false,
  })
  const state = readonly(mutableState)
  const deviceInstallationId = installationId()

  let currentToken: string | null = null
  let associatedUserId: string | null = null
  let associatedToken: string | null = null
  let mayBeAssociatedUserId: string | null = null
  let associationBlocked = false
  let lifecycleVersion = 0
  let permissionEpoch = 0
  let navigationReady = options.navigationReady?.value ?? false
  let disposed = false
  let activeAttempt: AssociationAttempt | null = null
  let lastReceivedIntent: DeliveryPushData | null = null

  function update(patch: Partial<PushState>): void {
    if (disposed) return
    mutableState.value = { ...mutableState.value, ...patch }
  }

  function currentUser(): AppUser | null {
    return options.user.value
  }

  function setPendingIntents(pending: readonly DeliveryPushData[]): void {
    update({ pendingNavigation: pending.length > 0 })
  }

  const coordinator = new DeliveryIntentCoordinator({
    navigate: options.onNavigate,
    onPendingChange: setPendingIntents,
    onOutcome: (intent) => {
      if (mutableState.value.banner?.eventId === intent.eventId) {
        update({ banner: null, error: null })
      }
    },
    onRouteError: () => {
      update({ error: pushCopy.routeFailed })
    },
  })

  function updateCoordinatorContext(): void {
    const user = currentUser()
    coordinator.setContext({
      userId: user?.id ?? null,
      householdId: user?.householdId ?? null,
      navigationReady,
    })
  }

  function canAssociate(user: AppUser | null): user is AppUser {
    return Boolean(
      user &&
      currentToken &&
      mutableState.value.permission === 'granted' &&
      !associationBlocked &&
      !disposed,
    )
  }

  async function associateCurrentToken(force = false): Promise<void> {
    const user = currentUser()
    const token = currentToken
    if (!canAssociate(user) || !token) return

    if (
      !force &&
      associatedUserId === user.id &&
      associatedToken === token &&
      mutableState.value.association === 'registered'
    ) {
      return
    }

    if (activeAttempt) {
      if (activeAttempt.userId === user.id && activeAttempt.token === token) {
        await activeAttempt.promise
        return
      }
      await activeAttempt.promise
      if (!canAssociate(currentUser()) || !currentToken) return
      return associateCurrentToken(force)
    }

    const version = lifecycleVersion
    const registration: PushRegistration = {
      installationId: deviceInstallationId,
      platform: 'android',
      token,
    }
    update({ association: 'pending', error: null })

    const attempt: AssociationAttempt = {
      userId: user.id,
      token,
      promise: Promise.resolve(),
    }
    // Treat a rejected request as possibly applied: a dropped response does not
    // prove that the server failed to update the installation.
    mayBeAssociatedUserId = user.id
    const promise = Promise.resolve()
      .then(() => options.service.upsert(registration))
      .then(() => {
        // Record the server-side owner even if auth changed while the request
        // was in flight. That forces an explicit detach before another account.
        associatedUserId = user.id
        associatedToken = token
        if (
          !disposed &&
          version === lifecycleVersion &&
          currentUser()?.id === user.id &&
          currentToken === token &&
          !associationBlocked
        ) {
          update({ association: 'registered', error: null })
        }
      })
      .catch(() => {
        if (
          !disposed &&
          version === lifecycleVersion &&
          currentUser()?.id === user.id &&
          !associationBlocked
        ) {
          update({ association: 'failed', error: pushCopy.associationFailed })
        }
      })
      .finally(() => {
        if (activeAttempt === attempt) activeAttempt = null
      })
    attempt.promise = promise
    activeAttempt = attempt
    await promise
  }

  async function registerWithBridge(): Promise<void> {
    try {
      await options.bridge.register()
      if (currentToken) await associateCurrentToken()
      else if (mutableState.value.association === 'idle') {
        update({ association: 'pending', error: null })
      }
    } catch {
      if (!associationBlocked) {
        update({ association: 'failed', error: pushCopy.associationFailed })
      }
    }
  }

  async function enable(): Promise<void> {
    if (disposed || mutableState.value.busy) return
    const requestEpoch = ++permissionEpoch
    update({ busy: true, error: null })
    try {
      const permission = await options.bridge.requestPermission()
      if (disposed || requestEpoch !== permissionEpoch) return
      update({ permission })
      if (permission !== 'granted') {
        if (!associationBlocked) update({ association: 'idle' })
        return
      }
      if (associationBlocked) {
        update({ association: 'blocked', error: pushCopy.associationBlocked })
        return
      }
      await registerWithBridge()
    } catch {
      update({ association: 'failed', error: pushCopy.associationFailed })
    } finally {
      update({ busy: false })
    }
  }

  async function detachBlockedAssociation(): Promise<boolean> {
    if (disposed || mutableState.value.busy) return false
    const pendingAttempt = activeAttempt
    update({ busy: true, association: 'blocked', error: null })
    try {
      if (pendingAttempt) await pendingAttempt.promise
      await options.service.detach(deviceInstallationId)
      associatedUserId = null
      associatedToken = null
      mayBeAssociatedUserId = null
      associationBlocked = false
      update({ association: 'idle', error: null })
      return true
    } catch {
      associationBlocked = true
      update({ association: 'blocked', error: pushCopy.associationBlocked })
      return false
    } finally {
      update({ busy: false })
    }
  }

  async function retry(): Promise<void> {
    if (disposed || mutableState.value.busy) return
    if (associationBlocked) {
      const detached = await detachBlockedAssociation()
      if (detached) await associateCurrentToken(true)
      return
    }
    if (mutableState.value.permission !== 'granted') {
      await enable()
      return
    }
    if (currentToken) {
      await associateCurrentToken(true)
      return
    }

    update({ busy: true, error: null })
    try {
      await registerWithBridge()
    } finally {
      update({ busy: false })
    }
  }

  function onReceived(payload: unknown): void {
    const validated = validateDeliveryPushData(payload)
    const user = currentUser()
    if (!validated || !user || validated.householdId !== user.householdId)
      return
    const intent = coordinator.acceptReceived(payload)
    if (!intent) return
    lastReceivedIntent = intent
    update({
      banner: { eventId: intent.eventId, deliveryId: intent.deliveryId },
      error: null,
    })
    try {
      void Promise.resolve(options.onRefresh()).catch(() => undefined)
    } catch {
      // A foreground refresh is best-effort; the current page stays in place.
    }
  }

  function onTapped(payload: unknown): void {
    coordinator.acceptTap(payload)
  }

  function onToken(value: string): void {
    if (!validToken(value) || value === currentToken) return
    currentToken = value
    if (mutableState.value.permission === 'granted') {
      if (currentUser() && !associationBlocked) {
        update({ association: 'pending', error: null })
      }
      void associateCurrentToken()
    }
  }

  function onBridgeError(): void {
    if (!associationBlocked) {
      update({ association: 'failed', error: pushCopy.associationFailed })
    }
  }

  const unsubscribe = options.bridge.subscribe({
    received: onReceived,
    tapped: onTapped,
    token: onToken,
    error: onBridgeError,
  })

  const stopUserWatch = watch(
    () =>
      [
        options.user.value?.id ?? null,
        options.user.value?.householdId ?? null,
      ] as const,
    ([userId, householdId], previous) => {
      const [previousUserId, previousHouseholdId] = previous ?? [null, null]
      const accountChanged =
        previousUserId !== null &&
        (userId !== previousUserId || householdId !== previousHouseholdId)

      if (accountChanged) {
        lifecycleVersion += 1
        coordinator.clear()
        lastReceivedIntent = null
        update({ banner: null, pendingNavigation: false, error: null })

        if (
          associatedUserId === previousUserId ||
          mayBeAssociatedUserId === previousUserId ||
          activeAttempt?.userId === previousUserId
        ) {
          associationBlocked = true
          update({
            association: 'blocked',
            error: pushCopy.associationBlocked,
          })
        } else if (userId === null && !associationBlocked) {
          update({ association: 'idle' })
        }
      }

      updateCoordinatorContext()
      if (userId && !associationBlocked) void associateCurrentToken()
    },
    { immediate: true, flush: 'sync' },
  )

  const stopNavigationWatch = options.navigationReady
    ? watch(
        options.navigationReady,
        (ready) => {
          navigationReady = ready
          updateCoordinatorContext()
        },
        { immediate: true },
      )
    : undefined

  if (mutableState.value.mode === 'unavailable') {
    update({ permission: 'unsupported' })
  } else {
    const initialPermissionEpoch = permissionEpoch
    void options.bridge
      .permission()
      .then((permission) => {
        if (!disposed && permissionEpoch === initialPermissionEpoch) {
          update({ permission })
          if (permission === 'granted' && currentToken) {
            void associateCurrentToken()
          }
        }
      })
      .catch(() => undefined)
  }

  function isSimulator(bridge: PushBridge): bridge is PushSimulator {
    return (
      bridge.kind === 'simulated' &&
      typeof (bridge as Partial<PushSimulator>).simulateReceived ===
        'function' &&
      typeof (bridge as Partial<PushSimulator>).simulateTap === 'function'
    )
  }

  function simulateReceived(payload: unknown): void {
    if (import.meta.env.DEV && isSimulator(options.bridge)) {
      options.bridge.simulateReceived(payload)
    }
  }

  function simulateTap(payload: unknown): void {
    if (import.meta.env.DEV && isSimulator(options.bridge)) {
      options.bridge.simulateTap(payload)
    }
  }

  function tapBanner(): void {
    const banner = mutableState.value.banner
    if (!banner) {
      coordinator.retryPending()
      return
    }
    if (coordinator.retryPending(banner.eventId)) return
    if (lastReceivedIntent?.eventId === banner.eventId) {
      coordinator.acceptTap(lastReceivedIntent)
    }
  }

  function dismissBanner(): void {
    lastReceivedIntent = null
    update({ banner: null })
  }

  function setNavigationReady(ready: boolean): void {
    navigationReady = ready
    updateCoordinatorContext()
  }

  async function beforeLogout(): Promise<boolean> {
    if (disposed) return false
    const user = currentUser()
    if (!user) return !associationBlocked

    const pendingAttempt = activeAttempt
    const possibleAssociation =
      associatedUserId !== null ||
      mayBeAssociatedUserId !== null ||
      pendingAttempt !== null ||
      associationBlocked
    coordinator.clear()
    lastReceivedIntent = null
    update({ banner: null, pendingNavigation: false, error: null })

    if (!possibleAssociation) return true

    associationBlocked = true
    lifecycleVersion += 1
    update({ association: 'blocked', busy: true, error: null })
    if (pendingAttempt) await pendingAttempt.promise

    try {
      await options.service.detach(deviceInstallationId)
      associatedUserId = null
      associatedToken = null
      mayBeAssociatedUserId = null
      associationBlocked = false
      update({ association: 'idle', error: null })
      return true
    } catch {
      associationBlocked = true
      update({ association: 'blocked', error: pushCopy.detachFailed })
      return false
    } finally {
      update({ busy: false })
    }
  }

  function dispose(): void {
    if (disposed) return
    disposed = true
    lifecycleVersion += 1
    permissionEpoch += 1
    unsubscribe()
    stopUserWatch()
    stopNavigationWatch?.()
    coordinator.dispose()
    lastReceivedIntent = null
    void options.bridge.dispose()
  }

  return {
    state,
    enable,
    retry,
    simulateReceived,
    simulateTap,
    tapBanner,
    dismissBanner,
    setNavigationReady,
    beforeLogout,
    dispose,
  }
}
