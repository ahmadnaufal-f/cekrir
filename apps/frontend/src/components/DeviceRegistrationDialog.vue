<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue'
import AppDialog from './AppDialog.vue'
import AppIcon from './AppIcon.vue'
import { adminCopy } from '../lib/admin-copy'
import { ServiceError, type AppServices } from '../services/contracts'
import type { CameraInput, DeviceInventory } from '../types/app'
import type { DeviceCategory, DeviceUser } from '../types/device-ui'

const props = defineProps<{
  services: Pick<AppServices, 'mode' | 'devices'>
  user: DeviceUser
  kind: DeviceCategory
  inventory: DeviceInventory
}>()

const emit = defineEmits<{
  registered: [inventory: DeviceInventory]
  sessionExpired: []
  close: []
}>()

const copy = adminCopy.devices
const validationCopy = {
  esp32NameRequired: 'Nama perangkat wajib diisi.',
  cameraNameRequired: 'Nama kamera wajib diisi.',
} as const
const pending = shallowRef(false)
const completion = shallowRef(false)
const esp32LimitReached = shallowRef(false)
const errorMessage = shallowRef('')
const noticeMessage = shallowRef('')
const esp32FieldError = shallowRef('')
const cameraFieldErrors = shallowRef<Record<string, string>>({})
const esp32Name = shallowRef('')
const cameraForm = reactive({ name: '', url: '', username: '', password: '' })
const credential = shallowRef<string | null>(null)
const credentialVisible = shallowRef(false)
const credentialNotice = shallowRef('')

const dialogTitle = computed(() =>
  props.kind === 'esp32' ? copy.esp32Title : copy.registerCameraTitle,
)
const dialogDescription = computed(() => {
  if (completion.value) return undefined
  return props.kind === 'esp32'
    ? copy.esp32Description
    : copy.camerasDescription
})
const nameField = useTemplateRef<HTMLInputElement>('nameField')
const completionHeading =
  useTemplateRef<HTMLHeadingElement>('completionHeading')
const connectionDetails =
  useTemplateRef<HTMLDetailsElement>('connectionDetails')

let requestGeneration = 0
let activeMutationGeneration: number | null = null
let disposed = false

function isCurrent(generation: number): boolean {
  return (
    !disposed && generation === requestGeneration && props.user.role === 'admin'
  )
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

function resetDialogState(): void {
  completion.value = false
  esp32LimitReached.value = false
  errorMessage.value = ''
  noticeMessage.value = ''
  esp32FieldError.value = ''
  cameraFieldErrors.value = {}
  esp32Name.value = ''
  cameraForm.name = ''
  cameraForm.url = ''
  cameraForm.username = ''
  clearSensitiveState()
}

function finishMutation(generation: number): void {
  if (activeMutationGeneration !== generation) return
  activeMutationGeneration = null
  pending.value = false
}

function reportUnauthorized(cause: unknown, generation: number): void {
  if (isCurrent(generation) && isUnauthorized(cause)) emit('sessionExpired')
}

function errorForField(
  errors: Record<string, string>,
  ...keys: string[]
): string {
  for (const key of keys) {
    const message = errors[key]
    if (message) return message
  }
  return ''
}

async function registerEsp32(): Promise<void> {
  if (props.user.role !== 'admin' || pending.value) return
  if (props.inventory.esp32) {
    noticeMessage.value = copy.esp32Limit
    return
  }

  const name = esp32Name.value.trim()
  esp32FieldError.value = ''
  errorMessage.value = ''
  noticeMessage.value = ''
  if (!name) {
    esp32FieldError.value = validationCopy.esp32NameRequired
    return
  }

  const generation = requestGeneration
  activeMutationGeneration = generation
  pending.value = true
  try {
    const result = await props.services.devices.registerEsp32(name)
    if (!isCurrent(generation)) return

    emit('registered', result.inventory)
    esp32Name.value = ''
    credential.value = result.credential || null
    credentialVisible.value = false
    credentialNotice.value = ''
    completion.value = true

    await nextTick()
    if (isCurrent(generation)) completionHeading.value?.focus()
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (cause instanceof ServiceError && cause.status === 422) {
      esp32FieldError.value = cause.fieldErrors.name || ''
    }

    if (isEsp32Limit(cause)) {
      esp32LimitReached.value = true
      noticeMessage.value = copy.esp32Limit
      try {
        const latest = await props.services.devices.inventory()
        if (isCurrent(generation)) emit('registered', latest)
      } catch (refreshCause) {
        if (!isCurrent(generation)) return
        errorMessage.value = copy.loadFailed
        if (isUnauthorized(refreshCause)) emit('sessionExpired')
      }
    } else {
      errorMessage.value = copy.esp32Failed
    }
    reportUnauthorized(cause, generation)
  } finally {
    finishMutation(generation)
  }
}

function cameraFieldError(
  field: 'name' | 'url' | 'username' | 'password',
): string {
  if (field === 'name') return cameraFieldErrors.value.name || ''
  return errorForField(
    cameraFieldErrors.value,
    `connection.${field}`,
    `connection_${field}`,
    field,
  )
}

async function registerCamera(): Promise<void> {
  if (props.user.role !== 'admin' || pending.value) return

  const name = cameraForm.name.trim()
  cameraFieldErrors.value = {}
  errorMessage.value = ''
  noticeMessage.value = ''
  if (!name) {
    cameraFieldErrors.value = { name: validationCopy.cameraNameRequired }
    return
  }

  const input: CameraInput = { name }
  const url = cameraForm.url.trim()
  const username = cameraForm.username.trim()
  if (url) {
    input.connection = {
      url,
      ...(username ? { username } : {}),
      ...(cameraForm.password ? { password: cameraForm.password } : {}),
    }
  }
  cameraForm.password = ''

  const generation = requestGeneration
  activeMutationGeneration = generation
  pending.value = true
  try {
    const result = await props.services.devices.registerCamera(input)
    if (!isCurrent(generation)) return

    emit('registered', result)
    finishMutation(generation)
    closeDialog()
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (cause instanceof ServiceError && cause.status === 422) {
      cameraFieldErrors.value = cause.fieldErrors
      if (
        Object.keys(cause.fieldErrors).some(
          (field) =>
            field === 'connection' ||
            field.startsWith('connection.') ||
            field.startsWith('connection_') ||
            ['url', 'username', 'password'].includes(field),
        )
      ) {
        await nextTick()
        if (!isCurrent(generation)) return
        if (connectionDetails.value) connectionDetails.value.open = true
      }
    }
    errorMessage.value = copy.cameraFailed
    reportUnauthorized(cause, generation)
  } finally {
    finishMutation(generation)
  }
}

function closeDialog(): void {
  if (pending.value) return
  requestGeneration += 1
  resetDialogState()
  emit('close')
}

async function copyCredential(): Promise<void> {
  const value = credential.value
  if (!value || pending.value) return
  const generation = requestGeneration
  try {
    if (!navigator.clipboard?.writeText)
      throw new Error('Clipboard unavailable')
    await navigator.clipboard.writeText(value)
    if (isCurrent(generation) && credential.value === value)
      credentialNotice.value = copy.credentialCopied
  } catch {
    if (isCurrent(generation) && credential.value === value)
      credentialNotice.value = copy.credentialCopyFailed
  }
}

watch(
  [
    () => props.user.id,
    () => props.user.householdId,
    () => props.user.role,
    () => props.kind,
    () => props.services,
  ],
  () => {
    requestGeneration += 1
    resetDialogState()
  },
  { immediate: true, flush: 'sync' },
)

onMounted(async () => {
  await nextTick()
  if (!disposed && !completion.value) nameField.value?.focus()
})

onUnmounted(() => {
  disposed = true
  requestGeneration += 1
  activeMutationGeneration = null
  pending.value = false
  resetDialogState()
})
</script>

<template>
  <AppDialog
    :title="dialogTitle"
    :description="dialogDescription"
    :busy="pending"
    @close="closeDialog"
  >
    <section
      v-if="completion"
      class="registration-completion"
      aria-labelledby="registration-completion-title"
    >
      <h3
        id="registration-completion-title"
        ref="completionHeading"
        class="registration-completion__title"
        tabindex="-1"
      >
        {{ copy.credentialTitle }}
      </h3>
      <p class="registration-completion__intro">{{ copy.credentialIntro }}</p>
      <p
        v-if="!credential"
        class="registration-message registration-message--warning"
        role="alert"
      >
        {{ copy.credentialMissing }}
      </p>
      <p
        v-if="credential && props.services.mode === 'mock'"
        class="registration-completion__mock-label"
        role="note"
      >
        {{ copy.demoCredentialLabel }}
      </p>
      <p v-else-if="credential" class="registration-completion__device-label">
        {{ copy.esp32Title }}
      </p>

      <label v-if="credential" class="registration-field">
        <span>{{ copy.identity }}</span>
        <input :value="props.inventory.esp32?.id ?? ''" readonly />
      </label>
      <label v-if="credential" class="registration-field">
        <span>{{ copy.credentialLabel }}</span>
        <input
          :type="credentialVisible ? 'text' : 'password'"
          :value="credential"
          readonly
          autocomplete="off"
          :aria-label="copy.credentialInputLabel"
        />
      </label>
      <div v-if="credential" class="registration-actions">
        <button
          class="registration-button registration-button--quiet"
          type="button"
          :disabled="pending"
          @click="credentialVisible = !credentialVisible"
        >
          <AppIcon :name="credentialVisible ? 'eyeOff' : 'eye'" />
          {{ credentialVisible ? copy.hideCredential : copy.showCredential }}
        </button>
        <button
          class="registration-button registration-button--primary"
          type="button"
          :disabled="pending"
          @click="copyCredential"
        >
          <AppIcon name="copy" />
          {{ copy.copyCredential }}
        </button>
      </div>
      <p v-if="credentialNotice" class="registration-notice" role="status">
        {{ credentialNotice }}
      </p>
      <button
        class="registration-button registration-button--quiet registration-completion__dismiss"
        type="button"
        :disabled="pending"
        @click="closeDialog"
      >
        <AppIcon name="check" />
        {{ copy.credentialDismiss }}
      </button>
    </section>

    <form
      v-else-if="props.kind === 'esp32'"
      class="registration-form"
      :aria-busy="pending || undefined"
      @submit.prevent="registerEsp32"
    >
      <p
        v-if="errorMessage"
        class="registration-message registration-message--error"
        role="alert"
      >
        {{ errorMessage }}
      </p>
      <p
        v-if="props.inventory.esp32 || esp32LimitReached || noticeMessage"
        class="registration-message"
        role="status"
      >
        {{ noticeMessage || copy.esp32Limit }}
      </p>
      <label class="registration-field">
        <span>{{ copy.esp32Name }}</span>
        <input
          ref="nameField"
          v-model.trim="esp32Name"
          required
          maxlength="80"
          :placeholder="copy.esp32NamePlaceholder"
          autocomplete="off"
          :aria-invalid="!!esp32FieldError"
          :aria-describedby="esp32FieldError ? 'esp32-name-error' : undefined"
        />
        <span
          v-if="esp32FieldError"
          id="esp32-name-error"
          class="registration-field__error"
        >
          {{ esp32FieldError }}
        </span>
      </label>
      <button
        class="registration-button registration-button--primary"
        type="submit"
        :disabled="
          pending ||
          !!props.inventory.esp32 ||
          esp32LimitReached ||
          props.user.role !== 'admin'
        "
      >
        <AppIcon name="plus" />
        {{ pending ? copy.savingEsp32 : copy.addEsp32 }}
      </button>
    </form>

    <form
      v-else
      class="registration-form"
      :aria-busy="pending || undefined"
      @submit.prevent="registerCamera"
    >
      <p
        v-if="errorMessage"
        class="registration-message registration-message--error"
        role="alert"
      >
        {{ errorMessage }}
      </p>
      <label class="registration-field">
        <span>{{ copy.cameraName }}</span>
        <input
          ref="nameField"
          v-model.trim="cameraForm.name"
          required
          maxlength="80"
          :placeholder="copy.cameraNamePlaceholder"
          autocomplete="off"
          :aria-invalid="!!cameraFieldError('name')"
          :aria-describedby="
            cameraFieldError('name') ? 'camera-name-error' : undefined
          "
        />
        <span
          v-if="cameraFieldError('name')"
          id="camera-name-error"
          class="registration-field__error"
        >
          {{ cameraFieldError('name') }}
        </span>
      </label>
      <details ref="connectionDetails" class="registration-details">
        <summary>{{ copy.connectionDetails }}</summary>
        <span
          v-if="cameraFieldErrors.connection"
          class="registration-field__error"
        >
          {{ cameraFieldErrors.connection }}
        </span>
        <div class="registration-details__fields">
          <label class="registration-field">
            <span>{{ copy.connectionUrl }}</span>
            <input
              v-model.trim="cameraForm.url"
              type="url"
              :placeholder="copy.connectionUrlPlaceholder"
              autocomplete="off"
              :aria-invalid="!!cameraFieldError('url')"
              :aria-describedby="
                cameraFieldError('url') ? 'camera-url-error' : undefined
              "
            />
            <span
              v-if="cameraFieldError('url')"
              id="camera-url-error"
              class="registration-field__error"
            >
              {{ cameraFieldError('url') }}
            </span>
          </label>
          <label class="registration-field">
            <span>{{ copy.connectionUsername }}</span>
            <input
              v-model.trim="cameraForm.username"
              autocomplete="off"
              :aria-invalid="!!cameraFieldError('username')"
              :aria-describedby="
                cameraFieldError('username')
                  ? 'camera-username-error'
                  : undefined
              "
            />
            <span
              v-if="cameraFieldError('username')"
              id="camera-username-error"
              class="registration-field__error"
            >
              {{ cameraFieldError('username') }}
            </span>
          </label>
          <label class="registration-field">
            <span>{{ copy.connectionPassword }}</span>
            <input
              v-model="cameraForm.password"
              type="password"
              autocomplete="off"
              :aria-invalid="!!cameraFieldError('password')"
              :aria-describedby="
                cameraFieldError('password')
                  ? 'camera-password-error'
                  : undefined
              "
            />
            <span
              v-if="cameraFieldError('password')"
              id="camera-password-error"
              class="registration-field__error"
            >
              {{ cameraFieldError('password') }}
            </span>
          </label>
          <p class="registration-help">{{ copy.connectionHelp }}</p>
        </div>
      </details>
      <button
        class="registration-button registration-button--primary"
        type="submit"
        :disabled="pending || props.user.role !== 'admin'"
      >
        <AppIcon name="plus" />
        {{ pending ? copy.savingCamera : copy.addCamera }}
      </button>
    </form>
  </AppDialog>
</template>

<style scoped>
.registration-form {
  display: grid;
  gap: 18px;
}

.registration-field {
  display: grid;
  gap: 8px;
  min-width: 0;
  margin: 0;
  color: #435d4c;
  font-size: 0.875rem;
  font-weight: 600;
}

.registration-field input {
  width: 100%;
  min-width: 0;
  min-height: 48px;
  margin: 0;
  padding: 11px 13px;
  border: 1px solid #d6ded0;
  border-radius: 7px;
  background: #fffefa;
  color: #233d37;
  font: inherit;
  font-size: 1rem;
}

.registration-field input::placeholder {
  color: #65725f;
}

.registration-field input:focus {
  outline: 2px solid #8da88e;
  outline-offset: 2px;
}

.registration-field input[readonly] {
  background: #f0f2e9;
}

.registration-field input[aria-invalid='true'] {
  border-color: #925b3a;
}

.registration-field__error {
  color: #8c4226;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.5;
}

.registration-message {
  padding: 13px 15px;
  border: 1px solid #d3ddc7;
  border-radius: 8px;
  background: #e9eedf;
  color: #526b46;
  font-size: 0.9375rem;
  line-height: 1.6;
}

.registration-message--error,
.registration-message--warning {
  border-color: #e6ccba;
  background: #f9e9df;
  color: #814a2d;
}

.registration-button {
  display: inline-flex;
  min-height: 46px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 15px;
  border: 0;
  border-radius: 7px;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
  text-align: center;
}

.registration-button--primary {
  background: #234e41;
  color: #f6f7ef;
}

.registration-button--primary:hover:not(:disabled) {
  background: #173e32;
}

.registration-button--quiet {
  background: #eef2e8;
  color: #435d4c;
}

.registration-button:disabled {
  cursor: default;
  opacity: 0.58;
}

.registration-details {
  margin: 0;
  color: #435d4c;
  font-size: 0.875rem;
}

.registration-details summary {
  min-height: 44px;
  padding: 10px 0;
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.registration-details summary:focus-visible,
.registration-completion__title:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 3px;
}

.registration-details__fields {
  display: grid;
  gap: 16px;
  padding-top: 9px;
}

.registration-help,
.registration-completion__intro {
  color: #53675a;
  font-size: 0.9375rem;
  line-height: 1.65;
}

.registration-completion {
  display: grid;
  gap: 16px;
}

.registration-completion__title {
  color: #233d37;
  font-size: 1.25rem;
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.3;
}

.registration-completion__mock-label,
.registration-completion__device-label {
  width: fit-content;
  max-width: 100%;
  padding: 8px 10px;
  border: 1px solid #d7dfd0;
  border-radius: 7px;
  background: #eef2e8;
  color: #435d4c;
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.4;
}

.registration-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.registration-notice {
  color: #435d4c;
  font-size: 0.875rem;
  line-height: 1.5;
}

.registration-completion__dismiss {
  justify-self: start;
  margin-top: 4px;
}

@media (max-width: 420px) {
  .registration-actions {
    display: grid;
  }

  .registration-actions .registration-button {
    width: 100%;
  }
}
</style>
