export type Role = 'admin' | 'member'
export type ResourceState = 'pending' | 'ready' | 'unavailable'
export interface DeliveryTotalsQuery {
  /** Calendar date (YYYY-MM-DD) in the supplied IANA time zone. */
  date: string
  timeZone: string
}
export interface DeliveryTotals extends DeliveryTotalsQuery {
  receivedToday: number
  receivedAllTime: number
}
export interface DeliveryListQuery {
  search?: string
}
export interface AppUser {
  id: string
  householdId: string
  role: Role
  displayName: string
  loginId: string
}
export interface DeliverySummary {
  id: string
  householdId: string
  trackingNumber: string
  courier: { code: string; name: string } | null
  scannedAt: string
  photoState: ResourceState
  trackingState: ResourceState
}
export interface TrackingEvent {
  occurredAt: string | null
  description: string
  location: string | null
}
export interface DeliveryDetail extends DeliverySummary {
  photoContentPath: string | null
  tracking: null | {
    service: string | null
    statusCode: string | null
    statusLabel: string | null
    senderName: string | null
    recipientName: string | null
    origin: string | null
    destination: string | null
    events: TrackingEvent[]
  }
}
export interface CameraSummary {
  id: string
  name: string
  configurationState: 'incomplete' | 'configured'
  verificationState: 'not_tested' | 'passed' | 'failed'
}
export interface DeviceInventory {
  esp32: null | { id: string; name: string }
  cameras: CameraSummary[]
  selectedDeliveryCameraId: string | null
}
export interface LoginInput {
  loginId: string
  password: string
}
export interface SignupInput {
  displayName: string
  email: string
  householdName: string
  password: string
}
export interface MemberInput {
  displayName: string
  loginId: string
  initialPassword: string
}
export interface CameraInput {
  name: string
  connection?: { url: string; username?: string; password?: string }
}
export interface DeviceRegistration {
  inventory: DeviceInventory
  credential: string
}
export interface SetupContent {
  kind: 'esp32' | 'bardi'
  readiness: 'scaffold' | 'pending'
  sourceUrl: string | null
  guideUrl: string | null
}
export interface PushRegistration {
  installationId: string
  platform: 'android'
  token: string
}
export interface DeliveryPushData {
  type: 'delivery.created'
  eventId: string
  deliveryId: string
  householdId: string
}
export type AppRoute =
  | '/login'
  | '/signup'
  | '/deliveries'
  | `/deliveries/${string}`
  | '/devices'
  | '/devices/setup/esp32'
  | '/devices/setup/cameras'
  | '/members'
  | '/setup'
  | '/settings'
