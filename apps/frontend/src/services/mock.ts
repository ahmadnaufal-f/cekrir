import type {
  AppUser,
  CameraInput,
  CameraSummary,
  DeliveryDetail,
  DeliverySummary,
  DeviceInventory,
  DeviceRegistration,
  LoginInput,
  MemberInput,
  PushRegistration,
  SetupContent,
  SignupInput,
} from '../types/app'
import {
  ServiceError,
  type AppServices,
  type CredentialStore,
} from './contracts'
import {
  DEMO_DELIVERIES,
  DEMO_DELIVERY_SVG,
  INITIAL_DEMO_INVENTORY,
  MOCK_DEMO_ACCOUNTS,
  OTHER_HOUSEHOLD_DELIVERY,
} from './mock-fixtures'

export { MOCK_DEMO_ACCOUNTS, MOCK_DELIVERY_IDS } from './mock-fixtures'

export interface MockServiceOptions {
  /** Smaller pages are useful for exercising cursor behaviour in a local demo. Default: 20. */
  pageSize?: number
}

export type MockFailurePoint =
  | 'esp32-registration'
  | 'camera-registration'
  | 'camera-selection'
  | 'push-upsert'
  | 'push-detach'

export interface MockHarnessControls {
  /** Restore all accounts and fixtures, and sign out the current session. */
  reset(): void
  /** Fail the next call at this operation boundary. Each failure is consumed once. */
  failNext(point: MockFailurePoint): void
  /** End the current in-memory session so the next protected call returns 401. */
  expireSession(): void
}

export interface MockHarness {
  services: AppServices
  controls: MockHarnessControls
}

interface AccountRecord {
  user: AppUser
  password: string
}

interface MutableInventory {
  esp32: DeviceInventory['esp32']
  cameras: CameraSummary[]
  selectedDeliveryCameraId: string | null
}

interface HouseholdRecord {
  inventory: MutableInventory
}

const DEFAULT_PAGE_SIZE = 20
const ERROR_COPY = {
  unauthenticated: 'Silakan masuk untuk melanjutkan.',
  invalidCredentials: 'ID masuk atau kata sandi tidak sesuai.',
  adminOnly: 'Tindakan ini hanya tersedia untuk admin rumah tangga.',
  retry: 'Operasi demo gagal. Silakan coba lagi.',
  householdMissing: 'Rumah tangga tidak ditemukan.',
  cursorInvalid: 'Penanda halaman daftar tidak valid.',
  deliveryMissing: 'Paket tidak ditemukan.',
  deliveryForbidden: 'Anda tidak memiliki akses ke paket ini.',
  cameraForbidden: 'Kamera ini milik rumah tangga lain.',
  cameraMissing: 'Kamera tidak ditemukan.',
  accountEmailExists: 'Akun dengan email ini sudah terdaftar.',
  accountLoginExists: 'ID masuk ini sudah digunakan.',
  esp32Limit: 'Setiap rumah tangga hanya dapat mendaftarkan satu ESP32.',
  photoPending: 'Ilustrasi demo masih disiapkan.',
  photoUnavailable: 'Foto tidak tersedia.',
  installationForbidden: 'Instalasi notifikasi ini terhubung ke akun lain.',
  validation: 'Periksa kembali isian Anda.',
  fields: {
    displayName: 'Nama wajib diisi.',
    email: 'Email wajib diisi.',
    householdName: 'Nama rumah tangga wajib diisi.',
    password: 'Kata sandi wajib diisi.',
    name: 'Nama perangkat wajib diisi.',
    loginId: 'ID masuk wajib diisi.',
    initialPassword: 'Kata sandi awal wajib diisi.',
    installationId: 'ID instalasi wajib diisi.',
    token: 'Token notifikasi wajib diisi.',
  },
} as const
type MockField = keyof typeof ERROR_COPY.fields

function cloneUser(user: AppUser): AppUser {
  return { ...user }
}

function cloneInventory(inventory: MutableInventory): DeviceInventory {
  return {
    esp32: inventory.esp32 ? { ...inventory.esp32 } : null,
    cameras: inventory.cameras.map((camera) => ({ ...camera })),
    selectedDeliveryCameraId: inventory.selectedDeliveryCameraId,
  }
}

function cloneDelivery(delivery: DeliveryDetail): DeliveryDetail {
  return {
    ...delivery,
    courier: delivery.courier ? { ...delivery.courier } : null,
    tracking: delivery.tracking
      ? {
          ...delivery.tracking,
          events: delivery.tracking.events.map((event) => ({ ...event })),
        }
      : null,
  }
}

function normalizeLoginId(loginId: string): string {
  return loginId.trim().toLocaleLowerCase('en-US')
}

function fieldError(field: MockField): ServiceError {
  return new ServiceError('VALIDATION_ERROR', ERROR_COPY.validation, 422, {
    [field]: ERROR_COPY.fields[field],
  })
}

export function createMockHarness(
  options: MockServiceOptions = {},
): MockHarness {
  const pageSize = options.pageSize ?? DEFAULT_PAGE_SIZE
  if (!Number.isInteger(pageSize) || pageSize < 1) {
    throw new RangeError('Mock pageSize must be a positive integer.')
  }

  const accountsById = new Map<string, AccountRecord>()
  const accountIdByLogin = new Map<string, string>()
  const households = new Map<string, HouseholdRecord>()
  const deliveries = new Map<string, DeliveryDetail>()
  const sessions = new Map<string, string>()
  const pushInstallations = new Map<
    string,
    { userId: string; registration: PushRegistration }
  >()
  const failures = new Map<MockFailurePoint, number>()
  let sessionSequence = 0
  let householdSequence = 0
  let memberSequence = 0
  let esp32Sequence = 0
  let cameraSequence = 0

  // This satisfies the draft CredentialStore boundary without browser storage.
  // It contains only an opaque, process-local session key and never a password.
  let sessionKey: string | null = null
  const credentialStore: CredentialStore = {
    read: () => sessionKey,
    write: (value) => {
      sessionKey = value
    },
    clear: () => {
      sessionKey = null
    },
  }

  function addAccount(user: AppUser, password: string): void {
    accountsById.set(user.id, { user, password })
    accountIdByLogin.set(normalizeLoginId(user.loginId), user.id)
  }

  function seed(): void {
    accountsById.clear()
    accountIdByLogin.clear()
    households.clear()
    deliveries.clear()
    sessions.clear()
    pushInstallations.clear()
    failures.clear()
    credentialStore.clear()
    sessionSequence = 0
    householdSequence = 0
    memberSequence = 0
    esp32Sequence = 0
    cameraSequence = 0

    addAccount(
      {
        id: 'user-demo-admin',
        householdId: 'household-demo',
        role: 'admin',
        displayName: 'Admin Demo',
        loginId: MOCK_DEMO_ACCOUNTS.admin.loginId,
      },
      MOCK_DEMO_ACCOUNTS.admin.password,
    )
    addAccount(
      {
        id: 'user-demo-member',
        householdId: 'household-demo',
        role: 'member',
        displayName: 'Anggota Demo',
        loginId: MOCK_DEMO_ACCOUNTS.member.loginId,
      },
      MOCK_DEMO_ACCOUNTS.member.password,
    )
    addAccount(
      {
        id: 'user-tetangga',
        householdId: 'household-tetangga',
        role: 'member',
        displayName: 'Tetangga Demo',
        loginId: MOCK_DEMO_ACCOUNTS.otherHousehold.loginId,
      },
      MOCK_DEMO_ACCOUNTS.otherHousehold.password,
    )

    households.set('household-demo', {
      inventory: {
        esp32: INITIAL_DEMO_INVENTORY.esp32
          ? { ...INITIAL_DEMO_INVENTORY.esp32 }
          : null,
        cameras: INITIAL_DEMO_INVENTORY.cameras.map((camera) => ({
          ...camera,
        })),
        selectedDeliveryCameraId:
          INITIAL_DEMO_INVENTORY.selectedDeliveryCameraId,
      },
    })
    households.set('household-tetangga', {
      inventory: { esp32: null, cameras: [], selectedDeliveryCameraId: null },
    })
    for (const delivery of DEMO_DELIVERIES)
      deliveries.set(delivery.id, cloneDelivery(delivery))
    deliveries.set(
      OTHER_HOUSEHOLD_DELIVERY.id,
      cloneDelivery(OTHER_HOUSEHOLD_DELIVERY),
    )
  }

  function injectFailure(point: MockFailurePoint): void {
    const remaining = failures.get(point) ?? 0
    if (remaining < 1) return
    if (remaining === 1) failures.delete(point)
    else failures.set(point, remaining - 1)
    throw new ServiceError('MOCK_OPERATION_FAILED', ERROR_COPY.retry, 503)
  }

  function currentUser(): AppUser {
    const key = credentialStore.read()
    const userId = key ? sessions.get(key) : undefined
    const record = userId ? accountsById.get(userId) : undefined
    if (!record)
      throw new ServiceError('UNAUTHENTICATED', ERROR_COPY.unauthenticated, 401)
    return record.user
  }

  function requireAdmin(): AppUser {
    const user = currentUser()
    if (user.role !== 'admin') {
      throw new ServiceError('FORBIDDEN', ERROR_COPY.adminOnly, 403)
    }
    return user
  }

  function issueSession(user: AppUser): void {
    const key = `mock-session-${++sessionSequence}`
    sessions.set(key, user.id)
    credentialStore.write(key)
  }

  function findCameraOwner(cameraId: string): string | undefined {
    for (const [householdId, household] of households) {
      if (household.inventory.cameras.some((camera) => camera.id === cameraId))
        return householdId
    }
    return undefined
  }

  function getHousehold(user: AppUser): HouseholdRecord {
    const household = households.get(user.householdId)
    if (!household)
      throw new ServiceError('NOT_FOUND', ERROR_COPY.householdMissing, 404)
    return household
  }

  const services: AppServices = {
    mode: 'mock',
    auth: {
      async restore(): Promise<AppUser | null> {
        const key = credentialStore.read()
        const userId = key ? sessions.get(key) : undefined
        const record = userId ? accountsById.get(userId) : undefined
        if (!record) {
          credentialStore.clear()
          return null
        }
        return cloneUser(record.user)
      },
      async login(input: LoginInput): Promise<AppUser> {
        const loginId = normalizeLoginId(input.loginId)
        const userId = accountIdByLogin.get(loginId)
        const record = userId ? accountsById.get(userId) : undefined
        if (!record || record.password !== input.password) {
          throw new ServiceError(
            'INVALID_CREDENTIALS',
            ERROR_COPY.invalidCredentials,
            401,
          )
        }
        issueSession(record.user)
        return cloneUser(record.user)
      },
      async signup(input: SignupInput): Promise<AppUser> {
        const loginId = normalizeLoginId(input.email)
        if (!input.displayName.trim()) throw fieldError('displayName')
        if (!loginId) throw fieldError('email')
        if (!input.householdName.trim()) throw fieldError('householdName')
        if (!input.password) throw fieldError('password')
        if (accountIdByLogin.has(loginId)) {
          throw new ServiceError(
            'ACCOUNT_EXISTS',
            ERROR_COPY.accountEmailExists,
            409,
            {
              email: ERROR_COPY.fields.email,
            },
          )
        }
        const householdId = `household-new-${++householdSequence}`
        const user: AppUser = {
          id: `user-new-admin-${householdSequence}`,
          householdId,
          role: 'admin',
          displayName: input.displayName.trim(),
          loginId,
        }
        households.set(householdId, {
          inventory: {
            esp32: null,
            cameras: [],
            selectedDeliveryCameraId: null,
          },
        })
        addAccount(user, input.password)
        issueSession(user)
        return cloneUser(user)
      },
      async logout(): Promise<void> {
        const key = credentialStore.read()
        if (key) sessions.delete(key)
        credentialStore.clear()
      },
    },
    deliveries: {
      async list(
        cursor?: string,
      ): Promise<{ items: DeliverySummary[]; nextCursor: string | null }> {
        const user = currentUser()
        const items = [...deliveries.values()]
          .filter((delivery) => delivery.householdId === user.householdId)
          .sort(
            (a, b) =>
              b.scannedAt.localeCompare(a.scannedAt) ||
              a.id.localeCompare(b.id),
          )
        let start = 0
        if (cursor) {
          const cursorIndex = items.findIndex(
            (delivery) => delivery.id === cursor,
          )
          if (cursorIndex < 0) {
            throw new ServiceError(
              'INVALID_CURSOR',
              ERROR_COPY.cursorInvalid,
              400,
            )
          }
          start = cursorIndex + 1
        }
        const page = items.slice(start, start + pageSize)
        const hasMore = start + page.length < items.length
        const summaries: DeliverySummary[] = page.map((delivery) => ({
          id: delivery.id,
          householdId: delivery.householdId,
          trackingNumber: delivery.trackingNumber,
          courier: delivery.courier ? { ...delivery.courier } : null,
          scannedAt: delivery.scannedAt,
          photoState: delivery.photoState,
          trackingState: delivery.trackingState,
        }))
        return {
          items: summaries,
          nextCursor: hasMore ? (page.at(-1)?.id ?? null) : null,
        }
      },
      async detail(id: string): Promise<DeliveryDetail> {
        const user = currentUser()
        const delivery = deliveries.get(id)
        if (!delivery)
          throw new ServiceError(
            'DELIVERY_NOT_FOUND',
            ERROR_COPY.deliveryMissing,
            404,
          )
        if (delivery.householdId !== user.householdId) {
          throw new ServiceError('FORBIDDEN', ERROR_COPY.deliveryForbidden, 403)
        }
        return cloneDelivery(delivery)
      },
      async photo(id: string): Promise<Blob> {
        const user = currentUser()
        const delivery = deliveries.get(id)
        if (!delivery)
          throw new ServiceError(
            'DELIVERY_NOT_FOUND',
            ERROR_COPY.deliveryMissing,
            404,
          )
        if (delivery.householdId !== user.householdId) {
          throw new ServiceError('FORBIDDEN', ERROR_COPY.deliveryForbidden, 403)
        }
        if (delivery.photoState === 'pending') {
          throw new ServiceError('PHOTO_PENDING', ERROR_COPY.photoPending, 425)
        }
        if (delivery.photoState === 'unavailable') {
          throw new ServiceError(
            'PHOTO_UNAVAILABLE',
            ERROR_COPY.photoUnavailable,
            503,
          )
        }
        return new Blob([DEMO_DELIVERY_SVG], { type: 'image/svg+xml' })
      },
    },
    devices: {
      async inventory(): Promise<DeviceInventory> {
        const user = requireAdmin()
        return cloneInventory(getHousehold(user).inventory)
      },
      async registerEsp32(name: string): Promise<DeviceRegistration> {
        const user = requireAdmin()
        const household = getHousehold(user)
        if (!name.trim()) throw fieldError('name')
        if (household.inventory.esp32) {
          throw new ServiceError('ESP32_LIMIT', ERROR_COPY.esp32Limit, 409)
        }
        injectFailure('esp32-registration')
        const number = ++esp32Sequence
        household.inventory.esp32 = {
          id: `esp32-demo-${number}`,
          name: name.trim(),
        }
        return {
          inventory: cloneInventory(household.inventory),
          // A conspicuously fake, one-time display value. It is returned only here.
          credential: `DEMO-ONLY-NOT-VALID-DEVICE-CREDENTIAL-${number}`,
        }
      },
      async registerCamera(input: CameraInput): Promise<DeviceInventory> {
        const user = requireAdmin()
        const household = getHousehold(user)
        const name = input.name.trim()
        if (!name) throw fieldError('name')
        injectFailure('camera-registration')
        const configurationState = input.connection?.url.trim()
          ? 'configured'
          : 'incomplete'
        const camera: CameraSummary = {
          id: `camera-demo-new-${++cameraSequence}`,
          name,
          configurationState,
          verificationState: 'not_tested',
        }
        // Connection fields, including passwords, are deliberately discarded.
        household.inventory.cameras.push(camera)
        return cloneInventory(household.inventory)
      },
      async selectCamera(id: string): Promise<DeviceInventory> {
        const user = requireAdmin()
        const household = getHousehold(user)
        const owned = household.inventory.cameras.some(
          (camera) => camera.id === id,
        )
        if (!owned) {
          if (findCameraOwner(id)) {
            throw new ServiceError('FORBIDDEN', ERROR_COPY.cameraForbidden, 403)
          }
          throw new ServiceError(
            'CAMERA_NOT_FOUND',
            ERROR_COPY.cameraMissing,
            404,
          )
        }
        injectFailure('camera-selection')
        household.inventory.selectedDeliveryCameraId = id
        return cloneInventory(household.inventory)
      },
    },
    members: {
      async list(): Promise<AppUser[]> {
        const admin = requireAdmin()
        return [...accountsById.values()]
          .map((record) => record.user)
          .filter(
            (user) =>
              user.householdId === admin.householdId && user.role === 'member',
          )
          .map(cloneUser)
      },
      async create(input: MemberInput): Promise<AppUser> {
        const admin = requireAdmin()
        const displayName = input.displayName.trim()
        const loginId = normalizeLoginId(input.loginId)
        if (!displayName) throw fieldError('displayName')
        if (!loginId) throw fieldError('loginId')
        if (!input.initialPassword) throw fieldError('initialPassword')
        if (accountIdByLogin.has(loginId)) {
          throw new ServiceError(
            'ACCOUNT_EXISTS',
            ERROR_COPY.accountLoginExists,
            409,
            {
              loginId: ERROR_COPY.accountLoginExists,
            },
          )
        }
        const user: AppUser = {
          id: `user-demo-member-created-${++memberSequence}`,
          householdId: admin.householdId,
          role: 'member',
          displayName,
          loginId,
        }
        addAccount(user, input.initialPassword)
        // Creating credentials never replaces the admin's current session.
        return cloneUser(user)
      },
    },
    setup: {
      async content(kind: 'esp32' | 'bardi'): Promise<SetupContent> {
        requireAdmin()
        if (kind === 'esp32') {
          const base =
            'https://github.com/ahmadnaufal-f/cekrir/blob/bc45600de0906a4b7995ac71118025259072c8a5/apps/esp32'
          return {
            kind,
            readiness: 'scaffold',
            sourceUrl: `${base}/src/main.cpp`,
            guideUrl: `${base}/README.md`,
          }
        }
        return { kind, readiness: 'pending', sourceUrl: null, guideUrl: null }
      },
    },
    push: {
      async upsert(registration: PushRegistration): Promise<void> {
        const user = currentUser()
        if (!registration.installationId.trim())
          throw fieldError('installationId')
        if (!registration.token.trim()) throw fieldError('token')
        injectFailure('push-upsert')
        pushInstallations.set(registration.installationId, {
          userId: user.id,
          registration: { ...registration },
        })
      },
      async detach(installationId: string): Promise<void> {
        const user = currentUser()
        if (!installationId.trim()) throw fieldError('installationId')
        const current = pushInstallations.get(installationId)
        if (current && current.userId !== user.id) {
          throw new ServiceError(
            'FORBIDDEN',
            ERROR_COPY.installationForbidden,
            403,
          )
        }
        injectFailure('push-detach')
        if (current) pushInstallations.delete(installationId)
      },
    },
  }

  const controls: MockHarnessControls = {
    reset: seed,
    failNext(point): void {
      failures.set(point, (failures.get(point) ?? 0) + 1)
    },
    expireSession(): void {
      const key = credentialStore.read()
      if (key) sessions.delete(key)
      credentialStore.clear()
    },
  }

  seed()
  return { services, controls }
}

/** Convenience factory for app startup when no simulator controls are needed. */
export function createMockServices(options?: MockServiceOptions): AppServices {
  return createMockHarness(options).services
}
