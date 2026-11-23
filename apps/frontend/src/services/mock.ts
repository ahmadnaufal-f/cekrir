import type {
  AppUser,
  CameraInput,
  CameraSummary,
  DeliveryDetail,
  DeliveryListQuery,
  DeliverySummary,
  DeliveryTotals,
  DeliveryTotalsQuery,
  DeviceInventory,
  DeviceRegistration,
  LoginInput,
  MemberInput,
  PushRegistration,
  SetupContent,
  SignupInput,
} from '../types/app'
import { getCalendarDate } from '../lib/delivery-date'
import { normalizeDeliverySearch } from '../lib/delivery-search'
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
  deviceUser?: () => AppUser | null
}

export type MockFailurePoint =
  | 'esp32-registration'
  | 'esp32-rename'
  | 'esp32-removal'
  | 'camera-registration'
  | 'camera-update'
  | 'camera-removal'
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
  adminOnly: 'Tindakan ini hanya tersedia untuk admin lokasi penerimaan.',
  retry: 'Operasi demo gagal. Silakan coba lagi.',
  householdMissing: 'Lokasi penerimaan tidak ditemukan.',
  cursorInvalid: 'Penanda halaman daftar tidak valid.',
  deliveryMissing: 'Paket tidak ditemukan.',
  deliveryForbidden: 'Anda tidak memiliki akses ke paket ini.',
  cameraForbidden: 'Kamera ini terdaftar di lokasi penerimaan lain.',
  cameraMissing: 'Kamera tidak ditemukan.',
  accountEmailExists: 'Akun dengan email ini sudah terdaftar.',
  accountLoginExists: 'ID masuk ini sudah digunakan.',
  esp32Limit: 'Setiap lokasi penerimaan hanya dapat mendaftarkan satu ESP32.',
  esp32Missing: 'ESP32 tidak ditemukan.',
  photoPending: 'Ilustrasi demo masih disiapkan.',
  photoUnavailable: 'Foto tidak tersedia.',
  installationForbidden: 'Instalasi notifikasi ini terhubung ke akun lain.',
  validation: 'Periksa kembali isian Anda.',
  fields: {
    displayName: 'Nama wajib diisi.',
    email: 'Email wajib diisi.',
    householdName: 'Nama lokasi penerimaan wajib diisi.',
    password: 'Kata sandi wajib diisi.',
    name: 'Nama perangkat wajib diisi.',
    url: 'Isi alamat RTSP untuk mengganti detail koneksi.',
    loginId: 'ID masuk wajib diisi.',
    initialPassword: 'Kata sandi awal wajib diisi.',
    installationId: 'ID instalasi wajib diisi.',
    token: 'Token notifikasi wajib diisi.',
    date: 'Tanggal kalender tidak valid.',
    timeZone: 'Zona waktu tidak valid.',
    search: 'Kata pencarian tidak valid (maksimal 200 karakter).',
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

function isCalendarDate(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value))
    return false
  const parsed = new Date(`${value}T00:00:00.000Z`)
  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  )
}

function isTimeZone(value: unknown): value is string {
  if (typeof value !== 'string' || !value.trim()) return false
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: value })
    return true
  } catch {
    return false
  }
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

  function requireAdmin(user = currentUser()): AppUser {
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

  function deviceHousehold(): HouseholdRecord {
    const user = options.deviceUser ? options.deviceUser() : currentUser()
    if (!user)
      throw new ServiceError('UNAUTHENTICATED', ERROR_COPY.unauthenticated, 401)
    return getHousehold(requireAdmin(user))
  }

  function requireEsp32(inventory: MutableInventory, id: string) {
    const device = inventory.esp32
    if (!device || device.id !== id)
      throw new ServiceError('ESP32_NOT_FOUND', ERROR_COPY.esp32Missing, 404)
    return device
  }

  function requireCameraIndex(inventory: MutableInventory, id: string) {
    const index = inventory.cameras.findIndex((camera) => camera.id === id)
    if (index >= 0) return index
    if (findCameraOwner(id))
      throw new ServiceError('FORBIDDEN', ERROR_COPY.cameraForbidden, 403)
    throw new ServiceError('CAMERA_NOT_FOUND', ERROR_COPY.cameraMissing, 404)
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
      async totals(query: DeliveryTotalsQuery): Promise<DeliveryTotals> {
        const user = currentUser()
        if (!isCalendarDate(query?.date)) throw fieldError('date')
        if (!isTimeZone(query?.timeZone)) throw fieldError('timeZone')

        const householdDeliveries = [...deliveries.values()].filter(
          (delivery) => delivery.householdId === user.householdId,
        )
        return {
          date: query.date,
          timeZone: query.timeZone,
          receivedToday: householdDeliveries.filter(
            (delivery) =>
              getCalendarDate(new Date(delivery.scannedAt), query.timeZone) ===
              query.date,
          ).length,
          receivedAllTime: householdDeliveries.length,
        }
      },
      async list(
        cursor?: string,
        query?: DeliveryListQuery,
      ): Promise<{ items: DeliverySummary[]; nextCursor: string | null }> {
        const user = currentUser()
        if (
          query !== undefined &&
          (typeof query !== 'object' || query === null || Array.isArray(query))
        ) {
          throw fieldError('search')
        }
        const rawSearch: unknown = query?.search
        if (rawSearch !== undefined && typeof rawSearch !== 'string') {
          throw fieldError('search')
        }
        if (typeof rawSearch === 'string' && rawSearch.length > 200) {
          throw fieldError('search')
        }

        const search = normalizeDeliverySearch(rawSearch ?? '')
        const searchTokens = search ? search.split(' ') : []
        const items = [...deliveries.values()]
          .filter((delivery) => delivery.householdId === user.householdId)
          .filter((delivery) => {
            if (searchTokens.length === 0) return true
            const fields = normalizeDeliverySearch(
              [
                delivery.trackingNumber,
                delivery.courier?.name ?? '',
                delivery.courier?.code ?? '',
              ].join(' '),
            )
            return searchTokens.every((token) => fields.includes(token))
          })
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
        return cloneInventory(deviceHousehold().inventory)
      },
      async registerEsp32(name: string): Promise<DeviceRegistration> {
        const household = deviceHousehold()
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
      async renameEsp32(id: string, name: string): Promise<DeviceInventory> {
        const { inventory } = deviceHousehold()
        const device = requireEsp32(inventory, id)
        const label = name.trim()
        if (!label) throw fieldError('name')
        injectFailure('esp32-rename')
        inventory.esp32 = { ...device, name: label }
        return cloneInventory(inventory)
      },
      async removeEsp32(id: string): Promise<DeviceInventory> {
        const { inventory } = deviceHousehold()
        requireEsp32(inventory, id)
        injectFailure('esp32-removal')
        inventory.esp32 = null
        return cloneInventory(inventory)
      },
      async registerCamera(input: CameraInput): Promise<DeviceInventory> {
        const household = deviceHousehold()
        const name = input.name.trim()
        if (!name) throw fieldError('name')
        injectFailure('camera-registration')
        const configurationState = input.connection?.url.trim()
          ? 'configured'
          : 'incomplete'
        const camera: CameraSummary = {
          id: `camera-demo-new-${++cameraSequence}`,
          name,
          ...(input.tuyaDeviceId && { tuyaDeviceId: input.tuyaDeviceId }),
          configurationState,
          verificationState: 'not_tested',
        }
        // Connection fields, including passwords, are deliberately discarded.
        household.inventory.cameras.push(camera)
        return cloneInventory(household.inventory)
      },
      async updateCamera(
        id: string,
        input: CameraInput,
      ): Promise<DeviceInventory> {
        const { inventory } = deviceHousehold()
        const index = requireCameraIndex(inventory, id)
        const camera = inventory.cameras[index]!
        const name = input.name.trim()
        if (!name) throw fieldError('name')
        if (input.connection && !input.connection.url.trim())
          throw fieldError('url')
        injectFailure('camera-update')
        const metadata = {
          name,
          ...(input.tuyaDeviceId !== undefined && {
            tuyaDeviceId: input.tuyaDeviceId,
          }),
        }
        // Keep the saved state for a rename. Replacing connection details requires verification again.
        inventory.cameras[index] = input.connection
          ? {
              ...camera,
              ...metadata,
              configurationState: 'configured',
              verificationState: 'not_tested',
            }
          : { ...camera, ...metadata }
        return cloneInventory(inventory)
      },
      async removeCamera(id: string): Promise<DeviceInventory> {
        const { inventory } = deviceHousehold()
        const index = requireCameraIndex(inventory, id)
        injectFailure('camera-removal')
        inventory.cameras.splice(index, 1)
        if (inventory.selectedDeliveryCameraId === id)
          inventory.selectedDeliveryCameraId = null
        return cloneInventory(inventory)
      },
      async selectCamera(id: string): Promise<DeviceInventory> {
        const { inventory } = deviceHousehold()
        requireCameraIndex(inventory, id)
        injectFailure('camera-selection')
        inventory.selectedDeliveryCameraId = id
        return cloneInventory(inventory)
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
