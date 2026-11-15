import type {
  AppUser,
  LoginInput,
  SignupInput,
  DeliverySummary,
  DeliveryDetail,
  DeviceInventory,
  DeviceRegistration,
  CameraInput,
  MemberInput,
  SetupContent,
  PushRegistration,
} from '../types/app'

export class ServiceError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 0,
    public fieldErrors: Record<string, string> = {},
    public retryAfter?: string,
  ) {
    super(message)
    this.name = 'ServiceError'
  }
}
export interface CredentialStore {
  read(): string | null
  write(value: string): void
  clear(): void
}
export interface AuthService {
  restore(): Promise<AppUser | null>
  login(input: LoginInput): Promise<AppUser>
  signup(input: SignupInput): Promise<AppUser>
  logout(): Promise<void>
}
export interface DeliveryService {
  list(
    cursor?: string,
  ): Promise<{ items: DeliverySummary[]; nextCursor: string | null }>
  detail(id: string): Promise<DeliveryDetail>
  photo(id: string): Promise<Blob>
}
export interface DeviceService {
  inventory(): Promise<DeviceInventory>
  registerEsp32(name: string): Promise<DeviceRegistration>
  registerCamera(input: CameraInput): Promise<DeviceInventory>
  selectCamera(id: string): Promise<DeviceInventory>
}
export interface MemberService {
  list(): Promise<AppUser[]>
  create(input: MemberInput): Promise<AppUser>
}
export interface SetupService {
  content(kind: 'esp32' | 'bardi'): Promise<SetupContent>
}
export interface PushService {
  upsert(registration: PushRegistration): Promise<void>
  detach(installationId: string): Promise<void>
}
export interface AppServices {
  mode: 'mock' | 'live'
  auth: AuthService
  deliveries: DeliveryService
  devices: DeviceService
  members: MemberService
  setup: SetupService
  push: PushService
}
