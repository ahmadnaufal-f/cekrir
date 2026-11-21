import type { Shipment, PackageNotification, ResiInput } from '../../types/api'
import type { AppServices } from '../../services/contracts'
export type { Shipment, PackageNotification, ResiInput }
export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'member'
  is_active: boolean
  created_at: string
}
export interface Credentials {
  email: string
  password: string
}
export interface Registration extends Credentials {
  full_name: string
}
export interface TokenPair {
  access_token: string
  refresh_token: string
  expires_in: number
  refresh_expires_in: number
  token_type?: 'bearer'
  user: User
}
export interface VerificationPending {
  detail?: string
}
export interface Page<T> {
  items: T[]
  nextOffset: number | null
}
export interface ApiServices {
  mode: 'live' | 'mock'
  user(): User | null
  subscribe(listener: (user: User | null) => void): () => void
  devices?: AppServices['devices']
  auth: {
    login(input: Credentials): Promise<User>
    register(input: Registration): Promise<VerificationPending>
    resend(input: Credentials): Promise<VerificationPending>
    refresh(): Promise<User>
    logout(): void
  }
  shipments: {
    list(offset?: number, signal?: AbortSignal): Promise<Page<Shipment>>
    find(
      id: string,
      signal?: AbortSignal,
      reload?: boolean,
    ): Promise<Shipment | null>
    create(input: ResiInput): Promise<Shipment>
    refresh(id: string): Promise<Shipment>
  }
  notifications: {
    list(
      offset?: number,
      signal?: AbortSignal,
    ): Promise<Page<PackageNotification>>
    connect(handlers: {
      event(value: PackageNotification): void
      status(value: string): void
      ready(): void
    }): () => void
  }
  users: {
    list(): Promise<User[]>
    role(id: string, role: User['role']): Promise<User>
  }
}
export function validateRegistration(
  input: Registration,
): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!input.full_name.trim() || input.full_name.trim().length > 200)
    errors.full_name = 'Isi nama, maksimal 200 karakter.'
  if (
    !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.email.trim()) ||
    input.email.trim().length > 320
  )
    errors.email = 'Masukkan email yang valid.'
  if (
    Array.from(input.password).length < 12 ||
    new TextEncoder().encode(input.password).length > 72
  )
    errors.password = 'Gunakan minimal 12 karakter dan maksimal 72 byte UTF-8.'
  return errors
}
export function validateShipment(input: ResiInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!/^[a-z0-9_-]{2,32}$/.test(input.courier.trim().toLowerCase()))
    errors.courier = 'Kode kurir: 2–32 huruf, angka, _ atau -.'
  if (!/^[A-Za-z0-9-]{3,64}$/.test(input.resi_number.trim()))
    errors.resi_number = 'Resi: 3–64 huruf, angka atau -.'
  return errors
}
