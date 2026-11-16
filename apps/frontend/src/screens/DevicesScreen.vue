<script setup lang="ts">
import DeviceSetupGuide from '../components/DeviceSetupGuide.vue'
import AppIcon from '../components/AppIcon.vue'
import { computed, onUnmounted, reactive, shallowRef, watch } from 'vue'
import { adminCopy } from '../lib/admin-copy'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import { ServiceError } from '../services/contracts'
import type {
  AppUser,
  CameraInput,
  CameraSummary,
  DeviceInventory,
} from '../types/app'
import type { AppServices } from '../services/contracts'

const props = defineProps<{ services: AppServices; user: AppUser }>()
const emit = defineEmits<{ sessionExpired: [] }>()

type InventoryState = 'loading' | 'ready' | 'error'
type DeviceOperation = 'esp32' | 'camera' | 'select' | null

const copy = adminCopy.devices
const inventory = shallowRef<DeviceInventory | null>(null)
const inventoryState = shallowRef<InventoryState>('loading')
const operation = shallowRef<DeviceOperation>(null)
const errorMessage = shallowRef('')
const esp32FieldError = shallowRef('')
const cameraFieldErrors = shallowRef<Record<string, string>>({})
const noticeMessage = shallowRef('')
const credential = shallowRef<string | null>(null)
const credentialVisible = shallowRef(false)
const credentialNotice = shallowRef('')
const esp32HelpOpen = shallowRef(false)
const esp32Name = shallowRef('')
const cameraForm = reactive({ name: '', url: '', username: '', password: '' })
const isAdmin = computed(() => props.user.role === 'admin')
const isBusy = computed(() => operation.value !== null)
const selectedCameraId = computed(
  () => inventory.value?.selectedDeliveryCameraId ?? null,
)
const needsCameraGuide = computed(() => {
  const cameras = inventory.value?.cameras
  if (!cameras) return false
  return (
    cameras.length === 0 ||
    !cameras.some((camera) => camera.id === selectedCameraId.value) ||
    cameras.some((camera) => camera.configurationState === 'incomplete')
  )
})

let requestGeneration = 0
let disposed = false

function isCurrent(generation: number): boolean {
  return !disposed && generation === requestGeneration && isAdmin.value
}

function isUnauthorized(cause: unknown): boolean {
  return cause instanceof ServiceError
    ? cause.status === 401 || cause.code === 'UNAUTHENTICATED'
    : typeof cause === 'object' &&
        cause !== null &&
        'status' in cause &&
        cause.status === 401
}

function isEsp32Limit(cause: unknown): boolean {
  return cause instanceof ServiceError
    ? cause.status === 409 || cause.code === 'ESP32_LIMIT_REACHED'
    : typeof cause === 'object' &&
        cause !== null &&
        'status' in cause &&
        cause.status === 409
}

function clearSensitiveState(): void {
  credential.value = null
  credentialVisible.value = false
  credentialNotice.value = ''
  cameraForm.password = ''
}

function resetScreenState(): void {
  inventory.value = null
  inventoryState.value = 'loading'
  operation.value = null
  errorMessage.value = ''
  esp32FieldError.value = ''
  cameraFieldErrors.value = {}
  noticeMessage.value = ''
  esp32HelpOpen.value = false
  esp32Name.value = ''
  cameraForm.name = ''
  cameraForm.url = ''
  cameraForm.username = ''
  clearSensitiveState()
}

function reportUnauthorized(cause: unknown, generation: number): boolean {
  if (isCurrent(generation) && isUnauthorized(cause)) {
    emit('sessionExpired')
    return true
  }
  return false
}

async function loadInventory(generation: number): Promise<void> {
  inventoryState.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await props.services.devices.inventory()
    if (!isCurrent(generation)) return
    inventory.value = result
    inventoryState.value = 'ready'
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (!reportUnauthorized(cause, generation)) {
      inventoryState.value = 'error'
      errorMessage.value = copy.loadFailed
    }
  }
}

async function registerEsp32(): Promise<void> {
  if (!isAdmin.value || isBusy.value) return
  if (inventory.value?.esp32) {
    noticeMessage.value = copy.esp32Limit
    return
  }
  const name = esp32Name.value.trim()
  if (!name) return

  const generation = requestGeneration
  operation.value = 'esp32'
  esp32FieldError.value = ''
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const result = await props.services.devices.registerEsp32(name)
    if (!isCurrent(generation)) return
    inventory.value = result.inventory
    inventoryState.value = 'ready'
    esp32Name.value = ''
    if (result.credential) {
      credential.value = result.credential
      credentialVisible.value = false
      credentialNotice.value = ''
    } else {
      noticeMessage.value = copy.credentialMissing
    }
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (reportUnauthorized(cause, generation)) return
    if (cause instanceof ServiceError && cause.status === 422)
      esp32FieldError.value = cause.fieldErrors.name || ''
    if (isEsp32Limit(cause)) {
      noticeMessage.value = copy.esp32Limit
      try {
        const latest = await props.services.devices.inventory()
        if (isCurrent(generation)) {
          inventory.value = latest
          inventoryState.value = 'ready'
        }
      } catch (refreshCause) {
        if (reportUnauthorized(refreshCause, generation)) return
        if (isCurrent(generation) && !inventory.value) {
          inventoryState.value = 'error'
        }
      }
    } else {
      errorMessage.value = copy.esp32Failed
    }
  } finally {
    if (isCurrent(generation)) operation.value = null
  }
}

async function registerCamera(): Promise<void> {
  if (!isAdmin.value || isBusy.value) return
  const name = cameraForm.name.trim()
  if (!name) return

  const generation = requestGeneration
  const url = cameraForm.url.trim()
  const username = cameraForm.username.trim()
  const password = cameraForm.password
  cameraForm.password = ''
  const input: CameraInput = { name }
  if (url) {
    input.connection = {
      url,
      ...(username ? { username } : {}),
      ...(password ? { password } : {}),
    }
  }

  operation.value = 'camera'
  cameraFieldErrors.value = {}
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const result = await props.services.devices.registerCamera(input)
    if (!isCurrent(generation)) return
    inventory.value = result
    inventoryState.value = 'ready'
    cameraForm.name = ''
    cameraForm.url = ''
    cameraForm.username = ''
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (cause instanceof ServiceError && cause.status === 422)
      cameraFieldErrors.value = cause.fieldErrors
    if (!reportUnauthorized(cause, generation))
      errorMessage.value = copy.cameraFailed
  } finally {
    if (isCurrent(generation)) operation.value = null
  }
}

async function selectCamera(cameraId: string): Promise<void> {
  if (!isAdmin.value || isBusy.value) return
  if (!inventory.value?.cameras.some((camera) => camera.id === cameraId)) return

  const generation = requestGeneration
  operation.value = 'select'
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const result = await props.services.devices.selectCamera(cameraId)
    if (!isCurrent(generation)) return
    inventory.value = result
    inventoryState.value = 'ready'
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (!reportUnauthorized(cause, generation))
      errorMessage.value = copy.selectionFailed
  } finally {
    if (isCurrent(generation)) operation.value = null
  }
}

function dismissCredential(): void {
  clearSensitiveState()
}

function updateEsp32HelpOpen(event: Event): void {
  const disclosure = event.currentTarget
  if (disclosure instanceof HTMLDetailsElement)
    esp32HelpOpen.value = disclosure.open
}

async function copyCredential(): Promise<void> {
  const value = credential.value
  if (!value) return
  try {
    if (!navigator.clipboard?.writeText)
      throw new Error('Clipboard unavailable')
    await navigator.clipboard.writeText(value)
    credentialNotice.value = copy.credentialCopied
  } catch {
    credentialNotice.value = copy.credentialCopyFailed
  }
}

function cameraConfigurationLabel(camera: CameraSummary): string {
  return camera.configurationState === 'configured'
    ? copy.cameraConfigured
    : copy.cameraIncomplete
}

function cameraVerificationLabel(camera: CameraSummary): string {
  if (camera.verificationState === 'passed') return copy.verificationPassed
  if (camera.verificationState === 'failed') return copy.verificationFailed
  return copy.verificationNotTested
}

watch(
  [() => props.user.id, () => props.user.householdId, () => props.user.role],
  () => {
    requestGeneration += 1
    resetScreenState()
    if (isAdmin.value) void loadInventory(requestGeneration)
  },
  { immediate: true, flush: 'sync' },
)

onUnmounted(() => {
  disposed = true
  requestGeneration += 1
  clearSensitiveState()
})
</script>

<template>
  <section class="admin-screen devices-screen" aria-labelledby="devices-title">
    <header class="admin-screen__header">
      <h1 id="devices-title">{{ copy.title }}</h1>
      <p class="admin-screen__intro">{{ copy.intro }}</p>
    </header>

    <p
      v-if="!isAdmin"
      class="admin-screen__banner admin-screen__banner--error"
      role="alert"
    >
      {{ adminCopy.common.adminOnly }}
    </p>

    <template v-else>
      <p
        v-if="errorMessage"
        class="admin-screen__banner admin-screen__banner--error"
        role="alert"
      >
        {{ errorMessage }}
      </p>
      <p v-if="noticeMessage" class="admin-screen__banner" role="status">
        {{ noticeMessage }}
      </p>

      <section
        v-if="credential"
        class="admin-panel credential-panel"
        aria-labelledby="credential-title"
      >
        <h2 id="credential-title">{{ copy.credentialTitle }}</h2>
        <p class="admin-panel__copy">{{ copy.credentialIntro }}</p>
        <p
          v-if="services.mode === 'mock'"
          class="credential-panel__demo"
          role="note"
        >
          {{ copy.demoCredentialLabel }}
        </p>
        <p v-else class="credential-panel__device">{{ copy.esp32Title }}</p>
        <label class="credential-field">
          <span>{{ copy.identity }}</span>
          <input :value="inventory?.esp32?.id ?? ''" readonly />
        </label>
        <label class="credential-field">
          <span>{{ copy.credentialLabel }}</span>
          <input
            :type="credentialVisible ? 'text' : 'password'"
            :value="credential"
            readonly
            autocomplete="off"
            :aria-label="copy.credentialInputLabel"
          />
        </label>
        <div class="credential-panel__actions">
          <button
            class="admin-button admin-button--quiet"
            type="button"
            @click="credentialVisible = !credentialVisible"
          >
            <AppIcon :name="credentialVisible ? 'eyeOff' : 'eye'" />
            {{ credentialVisible ? copy.hideCredential : copy.showCredential }}
          </button>
          <button
            class="admin-button admin-button--primary"
            type="button"
            @click="copyCredential"
          >
            <AppIcon name="copy" />
            {{ copy.copyCredential }}
          </button>
        </div>
        <p v-if="credentialNotice" class="admin-panel__notice" role="status">
          {{ credentialNotice }}
        </p>
        <button
          class="admin-button admin-button--quiet credential-panel__dismiss"
          type="button"
          @click="dismissCredential"
        >
          <AppIcon name="check" />
          {{ copy.credentialDismiss }}
        </button>
      </section>

      <template v-else>
        <section class="admin-panel" aria-labelledby="esp32-heading">
          <div class="admin-panel__heading">
            <div>
              <h2 id="esp32-heading">
                <AppIcon name="device" /> {{ copy.esp32Title }}
              </h2>
            </div>
            <span v-if="inventory?.esp32" class="admin-pill">{{
              copy.registeredLabel
            }}</span>
          </div>
          <p class="admin-panel__copy">{{ copy.esp32Description }}</p>

          <DeviceSetupGuide
            v-if="inventoryState === 'ready' && !inventory?.esp32"
            :services="props.services"
            :user="props.user"
            kind="esp32"
            @session-expired="emit('sessionExpired')"
          />

          <p
            v-if="inventoryState === 'loading'"
            class="admin-screen__status"
            role="status"
          >
            {{ adminCopy.common.loading }}
          </p>
          <div v-else-if="inventoryState === 'error'" class="admin-empty">
            <p>{{ copy.loadFailed }}</p>
            <button
              class="admin-button admin-button--quiet"
              type="button"
              @click="loadInventory(requestGeneration)"
            >
              <AppIcon name="refresh" />
              {{ adminCopy.common.retry }}
            </button>
          </div>
          <div v-else-if="inventory?.esp32" class="device-summary">
            <div class="device-summary__body">
              <strong>{{ inventory.esp32.name }}</strong>
              <span>{{ copy.esp32Registered }}</span>
              <small>{{ copy.identity }} · {{ inventory.esp32.id }}</small>
            </div>
          </div>
          <details
            v-if="inventoryState === 'ready' && inventory?.esp32"
            :key="`${props.user.id}:${props.user.householdId}:${props.user.role}`"
            class="device-help-disclosure"
            @toggle="updateEsp32HelpOpen"
          >
            <summary>{{ deviceGuideCopy.esp32.disclosure }}</summary>
            <DeviceSetupGuide
              v-if="esp32HelpOpen"
              :services="props.services"
              :user="props.user"
              kind="esp32"
              @session-expired="emit('sessionExpired')"
            />
          </details>
          <form
            v-if="inventoryState === 'ready' && !inventory?.esp32"
            class="admin-form admin-form--inline"
            @submit.prevent="registerEsp32"
          >
            <label class="admin-field">
              <span>{{ copy.esp32Name }}</span>
              <input
                v-model.trim="esp32Name"
                required
                maxlength="80"
                :placeholder="copy.esp32NamePlaceholder"
                autocomplete="off"
                :aria-invalid="!!esp32FieldError"
                aria-describedby="esp32-name-error"
              />
              <span
                v-if="esp32FieldError"
                id="esp32-name-error"
                class="admin-field__error"
                >{{ esp32FieldError }}</span
              >
            </label>
            <button
              class="admin-button admin-button--primary"
              type="submit"
              :disabled="isBusy || inventoryState !== 'ready'"
            >
              <AppIcon name="plus" />
              {{ operation === 'esp32' ? copy.savingEsp32 : copy.addEsp32 }}
            </button>
          </form>
        </section>

        <section class="admin-panel" aria-labelledby="cameras-heading">
          <div class="admin-panel__heading">
            <div>
              <h2 id="cameras-heading">
                <AppIcon name="camera" /> {{ copy.camerasTitle }}
              </h2>
            </div>
            <span class="admin-pill">{{ inventory?.cameras.length ?? 0 }}</span>
          </div>
          <p class="admin-panel__copy">{{ copy.camerasDescription }}</p>

          <p
            v-if="inventoryState === 'loading'"
            class="admin-screen__status"
            role="status"
          >
            {{ adminCopy.common.loading }}
          </p>
          <div v-else-if="inventoryState === 'error'" class="admin-empty">
            <p>{{ copy.loadFailed }}</p>
            <button
              class="admin-button admin-button--quiet"
              type="button"
              @click="loadInventory(requestGeneration)"
            >
              <AppIcon name="refresh" />
              {{ adminCopy.common.retry }}
            </button>
          </div>
          <p v-else-if="!inventory?.cameras.length" class="admin-empty">
            {{ copy.camerasEmpty }}
          </p>
          <ul v-else class="camera-list">
            <li
              v-for="camera in inventory.cameras"
              :key="camera.id"
              class="camera-card"
            >
              <div class="camera-card__heading">
                <div>
                  <h3>{{ camera.name }}</h3>
                  <p>{{ cameraConfigurationLabel(camera) }}</p>
                </div>
                <span
                  class="camera-card__state"
                  :class="`camera-card__state--${camera.verificationState}`"
                >
                  {{ cameraVerificationLabel(camera) }}
                </span>
              </div>
              <div class="camera-card__footer">
                <span
                  v-if="selectedCameraId === camera.id"
                  class="selected-label"
                  aria-current="true"
                >
                  <AppIcon name="check" />
                  {{ copy.selectedCamera }}
                </span>
                <span v-else class="camera-card__not-selected">{{
                  copy.notSelected
                }}</span>
                <button
                  v-if="selectedCameraId !== camera.id"
                  class="admin-button admin-button--quiet"
                  type="button"
                  :disabled="isBusy"
                  @click="selectCamera(camera.id)"
                >
                  <AppIcon name="camera" />
                  {{
                    operation === 'select'
                      ? copy.selectingCamera
                      : copy.selectCamera
                  }}
                </button>
              </div>
            </li>
          </ul>

          <DeviceSetupGuide
            v-if="inventoryState === 'ready' && needsCameraGuide"
            :services="props.services"
            :user="props.user"
            kind="bardi"
            @session-expired="emit('sessionExpired')"
          />

          <form class="admin-form camera-form" @submit.prevent="registerCamera">
            <h3>{{ copy.registerCameraTitle }}</h3>
            <label class="admin-field">
              <span>{{ copy.cameraName }}</span>
              <input
                v-model.trim="cameraForm.name"
                required
                maxlength="80"
                :placeholder="copy.cameraNamePlaceholder"
                autocomplete="off"
                :aria-invalid="!!cameraFieldErrors.name"
                aria-describedby="camera-name-error"
              />
              <span
                v-if="cameraFieldErrors.name"
                id="camera-name-error"
                class="admin-field__error"
                >{{ cameraFieldErrors.name }}</span
              >
            </label>
            <details class="camera-form__details">
              <summary>{{ copy.connectionDetails }}</summary>
              <div class="camera-form__connection">
                <label class="admin-field">
                  <span>{{ copy.connectionUrl }}</span>
                  <input
                    v-model.trim="cameraForm.url"
                    type="url"
                    :placeholder="copy.connectionUrlPlaceholder"
                    autocomplete="off"
                  />
                </label>
                <label class="admin-field">
                  <span>{{ copy.connectionUsername }}</span>
                  <input
                    v-model.trim="cameraForm.username"
                    autocomplete="off"
                  />
                </label>
                <label class="admin-field">
                  <span>{{ copy.connectionPassword }}</span>
                  <input
                    v-model="cameraForm.password"
                    type="password"
                    autocomplete="off"
                  />
                </label>
                <p class="admin-field__help">{{ copy.connectionHelp }}</p>
              </div>
            </details>
            <button
              class="admin-button admin-button--primary"
              type="submit"
              :disabled="isBusy || inventoryState !== 'ready'"
            >
              <AppIcon name="plus" />
              {{ operation === 'camera' ? copy.savingCamera : copy.addCamera }}
            </button>
          </form>
        </section>
      </template>
    </template>
  </section>
</template>

<style scoped>
.admin-screen {
  width: min(100%, 920px);
  margin: 0 auto;
  padding: 44px 0 64px;
  color: #233d37;
}

.admin-screen__header {
  margin-bottom: 28px;
}

.admin-panel__label {
  color: #53675a;
  margin-bottom: 5px;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 1.7px;
  line-height: 1.5;
  text-transform: uppercase;
}

.admin-screen__header h1 {
  margin: 0 0 10px;
  font-size: 1.75rem;
  letter-spacing: -1.5px;
  line-height: 1.15;
}

.admin-screen__intro,
.admin-panel__copy {
  max-width: 640px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.7;
}

.admin-screen__banner {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #d3ddc7;
  border-radius: 8px;
  background: #e9eedf;
  color: #526b46;
  font-size: 0.875rem;
  line-height: 1.6;
}

.admin-screen__banner--error {
  border-color: #e6ccba;
  background: #f9e9df;
  color: #925b3a;
}

.admin-panel {
  margin-top: 18px;
  padding: clamp(20px, 4vw, 28px);
  border: 1px solid #e0e4d9;
  border-radius: 12px;
  background: #fffefa;
  box-shadow: 0 10px 28px #233d3708;
}

.admin-panel__heading,
.camera-card__heading,
.camera-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.admin-panel__heading h2,
.credential-panel h2 {
  margin-top: 5px;
  font-size: 1.25rem;
  letter-spacing: -0.5px;
}

.admin-panel__copy {
  margin-top: 12px;
  font-size: 0.875rem;
}

.admin-pill {
  flex: 0 0 auto;
  padding: 7px 10px;
  border: 1px solid #d7dfd0;
  border-radius: 999px;
  background: #eef2e8;
  color: #536c53;
  font-size: 0.8125rem;
}

.admin-screen__status,
.admin-empty {
  margin-top: 18px;
  padding: 16px;
  border: 1px dashed #cfd8ca;
  border-radius: 8px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.6;
}

.admin-empty .admin-button {
  margin-top: 12px;
}

.device-summary {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 18px;
  border-radius: 9px;
  background: #f0f2e9;
}

.device-summary__body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.device-summary__body strong {
  overflow-wrap: anywhere;
  font-size: 0.9375rem;
}

.device-summary__body span,
.device-summary__body small {
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.device-help-disclosure {
  margin-top: 16px;
  color: #536c53;
  font-size: 0.8125rem;
}

.device-help-disclosure summary {
  width: fit-content;
  min-height: 44px;
  padding: 11px 0;
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: #9aab94;
  text-underline-offset: 3px;
}

.device-help-disclosure :deep(.device-guide) {
  margin-top: 8px;
}

.admin-form {
  display: grid;
  gap: 14px;
  margin-top: 20px;
}

.admin-form--inline {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
}

.admin-field,
.credential-field {
  display: grid;
  gap: 7px;
  color: #435d4c;
  font-size: 0.8125rem;
  font-weight: 600;
}

.admin-field input,
.credential-field input {
  width: 100%;
  min-height: 46px;
  padding: 11px 13px;
  border: 1px solid #d6ded0;
  border-radius: 7px;
  background: #fffefa;
  color: #233d37;
  font: inherit;
  font-size: 0.875rem;
}

.admin-field input::placeholder {
  color: #53675a;
}

.admin-field input:focus,
.credential-field input:focus {
  outline: 2px solid #8da88e;
  outline-offset: 2px;
}

.admin-button {
  gap: 8px;
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  padding: 11px 15px;
  border: 0;
  border-radius: 7px;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: center;
}

.admin-button--primary {
  background: #234e41;
  color: #f6f7ef;
}

.admin-button--primary:hover:not(:disabled) {
  background: #173e32;
}

.admin-button--quiet {
  background: #eef2e8;
  color: #536c53;
}

.admin-button:disabled {
  cursor: default;
  opacity: 0.58;
}

.camera-list {
  display: grid;
  gap: 12px;
  margin: 20px 0 0;
  padding: 0;
  list-style: none;
}

.camera-card {
  min-width: 0;
  padding: 16px;
  border: 1px solid #e3e8dd;
  border-radius: 9px;
  background: #fbfcf7;
}

.camera-card__heading {
  align-items: flex-start;
}

.camera-card__heading h3,
.camera-form h3 {
  font-size: 0.9375rem;
  font-weight: 650;
}

.camera-card__heading p,
.camera-card__not-selected {
  margin-top: 5px;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.camera-card__state {
  max-width: 180px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f0efe6;
  color: #6f6342;
  font-size: 0.8125rem;
  line-height: 1.4;
  text-align: center;
}

.camera-card__state--passed {
  background: #e4efe6;
  color: #417453;
}

.camera-card__state--failed {
  background: #fae9df;
  color: #925b3a;
}

.camera-card__footer {
  margin-top: 15px;
  padding-top: 13px;
  border-top: 1px solid #e9ece3;
}

.selected-label {
  color: #426749;
  font-size: 0.8125rem;
  font-weight: 700;
}

.selected-label span {
  margin-right: 4px;
}

.camera-form {
  padding-top: 20px;
  border-top: 1px solid #e9ece3;
}

.camera-form__details {
  color: #536c53;
  font-size: 0.8125rem;
}

.camera-form__details summary {
  min-height: 40px;
  padding-top: 10px;
  cursor: pointer;
  font-weight: 600;
}

.camera-form__connection {
  display: grid;
  gap: 14px;
  padding: 10px 0 0;
}

.admin-field__help {
  margin-top: -5px;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.credential-panel {
  border-color: #d4dfcf;
  background: #f8faf4;
}

.credential-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.credential-field {
  margin-top: 18px;
}

.credential-panel__dismiss {
  margin-top: 20px;
}

.credential-panel__demo,
.credential-panel__device {
  display: inline-block;
  margin-top: 14px;
  padding: 7px 10px;
  border: 1px solid #d7dfd0;
  border-radius: 7px;
  background: #eef2e8;
  color: #536c53;
  font-size: 0.8125rem;
  font-weight: 600;
}

.admin-panel__notice {
  margin-top: 12px;
  color: #536c53;
  font-size: 0.8125rem;
}

@media (max-width: 620px) {
  .admin-screen {
    padding: 30px 0 48px;
  }

  .admin-form--inline {
    grid-template-columns: minmax(0, 1fr);
  }

  .admin-form--inline .admin-button {
    width: 100%;
  }

  .camera-card__heading {
    flex-direction: column;
  }

  .camera-card__footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
