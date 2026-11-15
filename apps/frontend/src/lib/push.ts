import type { DeliveryPushData } from '../types/app'

export type PushPermissionState =
  'not-requested' | 'granted' | 'denied' | 'unsupported'

export type PushBridgeKind = 'simulated' | 'unavailable' | 'native'

export interface PushBridgeListeners {
  received(payload: unknown): void
  tapped(payload: unknown): void
  token(token: string): void
  error(error: unknown): void
}

export interface PushBridge {
  readonly kind: PushBridgeKind
  subscribe(listeners: PushBridgeListeners): () => void
  permission(): Promise<PushPermissionState>
  requestPermission(): Promise<PushPermissionState>
  register(): Promise<void>
  dispose(): void | Promise<void>
}

export interface PushSimulator extends PushBridge {
  readonly kind: 'simulated'
  simulateReceived(payload: unknown): void
  simulateTap(payload: unknown): void
}

export interface DeliveryIntentContext {
  userId: string | null
  householdId: string | null
  navigationReady: boolean
}

export interface DeliveryIntentCallbacks {
  navigate(deliveryId: string): boolean | Promise<boolean>
  onPendingChange?(pending: readonly DeliveryPushData[]): void
  onOutcome?(intent: DeliveryPushData, outcome: 'accepted' | 'rejected'): void
  onRouteError?(intent: DeliveryPushData): void
}

const MAX_OPAQUE_ID_LENGTH = 128
const MAX_PENDING_INTENTS = 8
const MAX_REMEMBERED_EVENTS = 128
const OPAQUE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function opaqueId(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length > 0 &&
    value.length <= MAX_OPAQUE_ID_LENGTH &&
    OPAQUE_ID_PATTERN.test(value)
  )
}

/** Validate untrusted push data and return only the fields the app understands. */
export function validateDeliveryPushData(
  payload: unknown,
): DeliveryPushData | null {
  try {
    let source: unknown = payload
    if (isRecord(payload) && Object.hasOwn(payload, 'data')) {
      source = payload.data
    }
    if (!isRecord(source)) return null

    const { type, eventId, deliveryId, householdId } = source
    if (
      type !== 'delivery.created' ||
      !opaqueId(eventId) ||
      !opaqueId(deliveryId) ||
      !opaqueId(householdId)
    ) {
      return null
    }

    return { type, eventId, deliveryId, householdId }
  } catch {
    return null
  }
}

function rememberBounded(set: Set<string>, eventId: string): void {
  set.add(eventId)
  if (set.size > MAX_REMEMBERED_EVENTS) {
    const oldest = set.values().next().value
    if (oldest !== undefined) set.delete(oldest)
  }
}

/**
 * Owns validated, bounded delivery intents. It accepts no routes from a push;
 * the navigator receives only a delivery ID after the account and router are ready.
 */
export class DeliveryIntentCoordinator {
  private context: DeliveryIntentContext = {
    userId: null,
    householdId: null,
    navigationReady: false,
  }
  private queue: DeliveryPushData[] = []
  private receivedEvents = new Set<string>()
  private completedTaps = new Set<string>()
  private running = false
  private disposed = false
  private resumeAfterRun = false
  private contextVersion = 0

  constructor(private readonly callbacks: DeliveryIntentCallbacks) {}

  get pending(): readonly DeliveryPushData[] {
    return this.queue.map((intent) => ({ ...intent }))
  }

  acceptReceived(payload: unknown): DeliveryPushData | null {
    const intent = validateDeliveryPushData(payload)
    if (!intent || this.receivedEvents.has(intent.eventId)) return null
    rememberBounded(this.receivedEvents, intent.eventId)
    return intent
  }

  acceptTap(payload: unknown): DeliveryPushData | null {
    const intent = validateDeliveryPushData(payload)
    if (
      !intent ||
      this.completedTaps.has(intent.eventId) ||
      this.queue.some((queued) => queued.eventId === intent.eventId) ||
      this.queue.length >= MAX_PENDING_INTENTS
    ) {
      return null
    }

    this.queue.push(intent)
    this.publishQueue()
    void this.processQueue()
    return intent
  }

  setContext(context: DeliveryIntentContext): void {
    const identityChanged =
      this.context.userId !== context.userId ||
      this.context.householdId !== context.householdId
    if (identityChanged) {
      this.contextVersion += 1
      if (this.running) this.resumeAfterRun = true
    }
    this.context = { ...context }
    void this.processQueue()
  }

  retryPending(eventId?: string): boolean {
    const pending = this.queue[0]
    if (!pending || (eventId && pending.eventId !== eventId)) return false
    void this.processQueue()
    return true
  }

  hasPending(eventId: string): boolean {
    return this.queue.some((intent) => intent.eventId === eventId)
  }

  clear(): void {
    this.contextVersion += 1
    this.resumeAfterRun = false
    this.queue = []
    this.receivedEvents.clear()
    this.completedTaps.clear()
    this.context = {
      userId: null,
      householdId: null,
      navigationReady: false,
    }
    this.publishQueue()
  }

  dispose(): void {
    this.disposed = true
    this.clear()
  }

  private publishQueue(): void {
    this.callbacks.onPendingChange?.(this.pending)
  }

  private async processQueue(): Promise<void> {
    if (
      this.running ||
      this.disposed ||
      !this.context.userId ||
      !this.context.householdId ||
      !this.context.navigationReady
    ) {
      return
    }

    this.running = true
    try {
      while (this.queue.length > 0 && !this.disposed) {
        const intent = this.queue[0]
        if (!intent) break
        const context = this.context
        const contextVersion = this.contextVersion

        // A household mismatch is a final, explicit rejection. Backend route
        // loading still authorizes the delivery independently.
        if (intent.householdId !== context.householdId) {
          this.finish(intent, 'rejected')
          continue
        }

        let accepted: boolean
        try {
          accepted = await this.callbacks.navigate(intent.deliveryId)
        } catch {
          this.callbacks.onRouteError?.(intent)
          return
        }

        if (
          contextVersion !== this.contextVersion ||
          context.userId !== this.context.userId ||
          context.householdId !== this.context.householdId
        ) {
          return
        }
        this.finish(intent, accepted ? 'accepted' : 'rejected')
      }
    } finally {
      this.running = false
      if (this.resumeAfterRun) {
        this.resumeAfterRun = false
        queueMicrotask(() => void this.processQueue())
      }
    }
  }

  private finish(
    intent: DeliveryPushData,
    outcome: 'accepted' | 'rejected',
  ): void {
    if (this.queue[0]?.eventId !== intent.eventId) return
    this.queue.shift()
    rememberBounded(this.completedTaps, intent.eventId)
    this.callbacks.onOutcome?.(intent, outcome)
    this.publishQueue()
  }
}

class SingleListenerPushBridge {
  private listeners: PushBridgeListeners | null = null

  subscribe(listeners: PushBridgeListeners): () => void {
    if (this.listeners) {
      throw new Error('Push bridge listeners are already registered')
    }
    this.listeners = listeners
    let active = true
    return () => {
      if (!active) return
      active = false
      if (this.listeners === listeners) this.listeners = null
    }
  }

  protected emitReceived(payload: unknown): void {
    this.listeners?.received(payload)
  }

  protected emitTapped(payload: unknown): void {
    this.listeners?.tapped(payload)
  }

  protected emitToken(token: string): void {
    this.listeners?.token(token)
  }

  protected emitError(error: unknown): void {
    this.listeners?.error(error)
  }

  protected clearListeners(): void {
    this.listeners = null
  }
}

/** Browser and unconfigured native builds report unavailable honestly. */
export class UnavailablePushBridge
  extends SingleListenerPushBridge
  implements PushBridge
{
  readonly kind = 'unavailable' as const

  async permission(): Promise<PushPermissionState> {
    return 'unsupported'
  }

  async requestPermission(): Promise<PushPermissionState> {
    return 'unsupported'
  }

  async register(): Promise<void> {
    throw new Error('Native push is unavailable in this build')
  }

  dispose(): void {
    this.clearListeners()
  }
}

/** Explicit mock-only bridge. It never registers with an operating system. */
export class SimulatedPushBridge
  extends SingleListenerPushBridge
  implements PushSimulator
{
  readonly kind = 'simulated' as const
  private permissionState: PushPermissionState = 'not-requested'

  async permission(): Promise<PushPermissionState> {
    return this.permissionState
  }

  async requestPermission(): Promise<PushPermissionState> {
    this.permissionState = 'granted'
    return this.permissionState
  }

  async register(): Promise<void> {
    if (this.permissionState !== 'granted') {
      throw new Error('Simulated permission has not been granted')
    }
    this.emitToken('simulated-android-token')
  }

  simulateReceived(payload: unknown): void {
    this.emitReceived(payload)
  }

  simulateTap(payload: unknown): void {
    this.emitTapped(payload)
  }

  dispose(): void {
    this.clearListeners()
  }
}

export function createSimulatedPushBridge(): PushSimulator {
  return new SimulatedPushBridge()
}

export function createUnavailablePushBridge(): UnavailablePushBridge {
  return new UnavailablePushBridge()
}
