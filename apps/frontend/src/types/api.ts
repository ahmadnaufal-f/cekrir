export type ShipmentStatus =
  | 'pending'
  | 'in_transit'
  | 'delivered'
  | 'exception'

export interface TrackingEvent {
  occurred_at: string
  description: string
  location: string | null
}

export interface Shipment {
  id: string
  resi_number: string
  courier: string
  source: 'manual' | 'camera'
  camera_id: string | null
  status: ShipmentStatus
  summary: string
  provider: string
  history: TrackingEvent[]
  created_at: string
  checked_at: string
  last_detected_at: string | null
}

export interface ResiInput {
  resi_number: string
  courier: string
}

export interface PackageNotification {
  id: string
  shipment_id: string
  title: string
  message: string
  created_at: string
}
