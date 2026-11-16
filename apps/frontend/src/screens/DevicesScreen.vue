<script setup lang="ts">
import { computed, nextTick, onUnmounted, shallowRef, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import TabSelector from '../components/TabSelector.vue'
import DeviceRegistrationDialog from '../components/DeviceRegistrationDialog.vue'
import { adminCopy } from '../lib/admin-copy'
import { isDeviceSetupComplete } from '../lib/device-setup-state'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, CameraSummary, DeviceInventory } from '../types/app'
import type { DeviceCategory, SetupStatus, TabOption } from '../types/device-ui'

const props = defineProps<{
  services: AppServices
  user: AppUser
  category: DeviceCategory
  registrationRequest?: DeviceCategory | null
}>()
const emit = defineEmits<{
  sessionExpired: []
  'update:category': [category: DeviceCategory]
  guide: [category: DeviceCategory]
  registrationHandled: []
}>()

const categories: readonly DeviceCategory[] = ['esp32', 'bardi']
const copy = adminCopy.devices
const inventory = shallowRef<DeviceInventory | null>(null)
const inventoryState = shallowRef<'loading' | 'ready' | 'error'>('loading')
const selecting = shallowRef(false)
const errorMessage = shallowRef('')
const noticeMessage = shallowRef('')
const dialogKind = shallowRef<DeviceCategory | null>(null)
const isAdmin = computed(() => props.user.role === 'admin')
const selectedCameraId = computed(
  () => inventory.value?.selectedDeliveryCameraId ?? null,
)
function status(category: DeviceCategory): SetupStatus {
  if (inventoryState.value === 'loading') return 'loading'
  if (inventoryState.value === 'error' || !inventory.value) return 'error'
  return isDeviceSetupComplete(inventory.value, category)
    ? 'complete'
    : 'incomplete'
}
const tabs = computed<TabOption[]>(() => [
  {
    value: 'esp32',
    label: copy.esp32Tab,
    panelId: 'device-panel-esp32',
    status: status('esp32'),
  },
  {
    value: 'bardi',
    label: copy.cameraTab,
    panelId: 'device-panel-bardi',
    status: status('bardi'),
  },
])

let generation = 0
let disposed = false
function isCurrent(request: number) {
  return !disposed && request === generation && isAdmin.value
}
function reportUnauthorized(cause: unknown, request: number): boolean {
  const unauthorized =
    cause instanceof ServiceError
      ? cause.status === 401 || cause.code === 'UNAUTHENTICATED'
      : typeof cause === 'object' &&
        cause !== null &&
        'status' in cause &&
        cause.status === 401
  if (isCurrent(request) && unauthorized) {
    inventory.value = null
    dialogKind.value = null
    emit('sessionExpired')
    return true
  }
  return false
}
async function loadInventory() {
  const request = ++generation
  inventoryState.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await props.services.devices.inventory()
    if (!isCurrent(request)) return
    inventory.value = result
    inventoryState.value = 'ready'
  } catch (cause) {
    if (!isCurrent(request)) return
    if (!reportUnauthorized(cause, request)) {
      inventory.value = null
      inventoryState.value = 'error'
    }
  }
}
function chooseCategory(value: string) {
  if (value === 'esp32' || value === 'bardi') {
    errorMessage.value = ''
    noticeMessage.value = ''
    emit('update:category', value)
  }
}
function openRegistration(category = props.category) {
  if (
    !isAdmin.value ||
    !inventory.value ||
    selecting.value ||
    inventoryState.value !== 'ready'
  )
    return
  if (category === 'esp32' && inventory.value.esp32) {
    noticeMessage.value = copy.esp32Limit
    return
  }
  dialogKind.value = category
}
function registered(result: DeviceInventory) {
  inventory.value = result
  inventoryState.value = 'ready'
  errorMessage.value = ''
  noticeMessage.value = ''
}
async function closeRegistration() {
  dialogKind.value = null
  await nextTick()
  // Registering the only ESP32 removes its opener. Keep keyboard focus on its tab.
  if (document.activeElement === document.body)
    document
      .getElementById(`device-tabs-${props.category}`)
      ?.focus({ preventScroll: true })
}
async function selectCamera(cameraId: string) {
  if (
    !isAdmin.value ||
    selecting.value ||
    dialogKind.value ||
    !inventory.value?.cameras.some((camera) => camera.id === cameraId)
  )
    return
  const request = generation
  selecting.value = true
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const result = await props.services.devices.selectCamera(cameraId)
    if (isCurrent(request)) inventory.value = result
  } catch (cause) {
    if (!isCurrent(request)) return
    if (!reportUnauthorized(cause, request))
      errorMessage.value = copy.selectionFailed
  } finally {
    if (isCurrent(request)) selecting.value = false
  }
}
function cameraVerificationLabel(camera: CameraSummary): string {
  if (camera.verificationState === 'passed') return copy.verificationPassed
  if (camera.verificationState === 'failed') return copy.verificationFailed
  return copy.verificationNotTested
}
watch(
  () =>
    [
      props.user.id,
      props.user.householdId,
      props.user.role,
      props.services,
    ] as const,
  () => {
    generation++
    inventory.value = null
    selecting.value = false
    dialogKind.value = null
    noticeMessage.value = ''
    errorMessage.value = ''
    inventoryState.value = 'loading'
    if (isAdmin.value) void loadInventory()
  },
  { immediate: true, flush: 'sync' },
)
watch(
  () => [props.registrationRequest, inventoryState.value] as const,
  ([request, state]) => {
    if (request && state === 'ready') {
      openRegistration(request)
      emit('registrationHandled')
    }
  },
  { immediate: true },
)
onUnmounted(() => {
  disposed = true
  generation++
  inventory.value = null
})
</script>

<template>
  <section class="devices-screen" aria-labelledby="devices-title">
    <header class="devices-screen__header">
      <h1 id="devices-title">{{ copy.title }}</h1>
      <p>{{ copy.intro }}</p>
    </header>
    <p v-if="!isAdmin" class="banner banner--error" role="alert">
      {{ adminCopy.common.adminOnly }}
    </p>
    <template v-else>
      <TabSelector
        id="device-tabs"
        :model-value="category"
        :tabs="tabs"
        :label="copy.tabLabel"
        @update:model-value="chooseCategory"
      />
      <p class="devices-screen__status-note">{{ copy.setupStatusNote }}</p>
      <p v-if="errorMessage" class="banner banner--error" role="alert">
        {{ errorMessage }}
      </p>
      <p v-if="noticeMessage" class="banner" role="status">
        {{ noticeMessage }}
      </p>
      <section
        v-for="panelCategory in categories"
        v-show="category === panelCategory"
        :id="`device-panel-${panelCategory}`"
        :key="panelCategory"
        class="device-panel"
        role="tabpanel"
        :aria-labelledby="`device-tabs-${panelCategory}`"
        :aria-busy="inventoryState === 'loading'"
        tabindex="0"
      >
        <header class="device-panel__heading">
          <AppIcon :name="panelCategory === 'esp32' ? 'device' : 'camera'" />
          <h2>
            {{
              panelCategory === 'esp32' ? copy.esp32Title : copy.camerasTitle
            }}
          </h2>
        </header>
        <p class="device-panel__description">
          {{
            panelCategory === 'esp32'
              ? copy.esp32Description
              : copy.camerasDescription
          }}
        </p>
        <p
          v-if="inventoryState === 'loading'"
          class="device-panel__state"
          role="status"
        >
          {{ adminCopy.common.loading }}
        </p>
        <div
          v-else-if="inventoryState === 'error'"
          class="device-panel__state"
          role="alert"
        >
          <p>{{ copy.loadFailed }}</p>
          <button
            class="button button--quiet"
            type="button"
            @click="loadInventory"
          >
            <AppIcon name="refresh" />{{ adminCopy.common.retry }}
          </button>
        </div>
        <template v-else-if="inventory">
          <template v-if="panelCategory === 'esp32'">
            <div v-if="inventory.esp32" class="device-summary">
              <strong>{{ inventory.esp32.name }}</strong>
              <span>{{ copy.esp32Registered }}</span>
              <small>{{ copy.identity }} · {{ inventory.esp32.id }}</small>
            </div>
            <p v-else class="device-panel__empty">{{ copy.noEsp32 }}</p>
          </template>
          <template v-else>
            <p v-if="!inventory.cameras.length" class="device-panel__empty">
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
                    <p>
                      {{
                        camera.configurationState === 'configured'
                          ? copy.cameraConfigured
                          : copy.cameraIncomplete
                      }}
                    </p>
                  </div>
                  <span
                    class="camera-card__state"
                    :class="`camera-card__state--${camera.verificationState}`"
                    >{{ cameraVerificationLabel(camera) }}</span
                  >
                </div>
                <div class="camera-card__footer">
                  <span
                    v-if="selectedCameraId === camera.id"
                    class="selected-label"
                    aria-current="true"
                    ><AppIcon name="check" />{{ copy.selectedCamera }}</span
                  >
                  <span v-else class="camera-card__not-selected">{{
                    copy.notSelected
                  }}</span>
                  <button
                    v-if="selectedCameraId !== camera.id"
                    class="button button--quiet"
                    type="button"
                    :disabled="selecting"
                    @click="selectCamera(camera.id)"
                  >
                    <AppIcon name="camera" />{{
                      selecting ? copy.selectingCamera : copy.selectCamera
                    }}
                  </button>
                </div>
              </li>
            </ul>
          </template>
          <div class="device-panel__actions">
            <a
              v-if="!isDeviceSetupComplete(inventory, panelCategory)"
              class="button button--quiet device-panel__guide"
              :href="
                panelCategory === 'esp32'
                  ? '#/devices/setup/esp32'
                  : '#/devices/setup/cameras'
              "
              @click.prevent="emit('guide', panelCategory)"
            >
              <AppIcon name="book" />{{
                panelCategory === 'esp32' ? copy.guideEsp32 : copy.guideCamera
              }}
            </a>
            <button
              v-if="panelCategory === 'bardi' || !inventory.esp32"
              class="button button--primary"
              type="button"
              :disabled="selecting"
              @click="openRegistration(panelCategory)"
            >
              <AppIcon name="plus" />{{ copy.registerDevice }}
            </button>
          </div>
        </template>
      </section>
      <DeviceRegistrationDialog
        v-if="dialogKind && inventory"
        :services="services"
        :user="user"
        :kind="dialogKind"
        :inventory="inventory"
        @registered="registered"
        @close="closeRegistration"
        @session-expired="emit('sessionExpired')"
      />
    </template>
  </section>
</template>

<style scoped>
.devices-screen {
  width: min(100%, 820px);
  margin: 0 auto;
  padding: 42px 0 64px;
  color: #233d37;
}
.devices-screen__header {
  margin-bottom: 26px;
}
.devices-screen__header h1 {
  margin: 0 0 8px;
  font-size: 1.875rem;
  letter-spacing: -0.04em;
  line-height: 1.2;
}
.devices-screen__header p,
.device-panel__description {
  max-width: 65ch;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.7;
}
.devices-screen__status-note {
  margin: 12px 0 24px;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.6;
}
.device-panel {
  min-width: 0;
}
.device-panel__heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.device-panel__heading .app-icon {
  width: 24px;
  height: 24px;
}
.device-panel__heading h2 {
  margin: 0;
  font-size: 1.125rem;
  line-height: 1.4;
}
.device-panel__state {
  margin: 24px 0;
  padding: 20px;
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
  color: #53675a;
  line-height: 1.6;
}
.device-panel__state .button {
  margin-top: 14px;
}
.device-panel__empty {
  margin: 24px 0 0;
  color: #53675a;
  line-height: 1.6;
}
.device-panel__actions {
  display: grid;
  justify-items: start;
  gap: 12px;
  margin-top: 24px;
}
.device-panel__actions .button {
  min-height: 44px;
  max-width: 100%;
  gap: 8px;
  padding: 12px 18px;
  text-align: center;
  text-decoration: none;
  overflow-wrap: anywhere;
}
.device-summary {
  display: grid;
  gap: 7px;
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
  overflow-wrap: anywhere;
}
.device-summary span,
.device-summary small {
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.6;
}
.camera-list {
  display: grid;
  gap: 12px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}
.camera-card {
  min-width: 0;
  padding: 20px;
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
}
.camera-card__heading,
.camera-card__footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.camera-card__heading > div {
  min-width: 0;
}
.camera-card__heading h3 {
  margin: 0 0 5px;
  font-size: 0.9375rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.camera-card__heading p,
.camera-card__not-selected {
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.6;
}
.camera-card__state {
  flex-shrink: 0;
  max-width: 40%;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f0efe6;
  color: #6f6342;
  font-size: 0.8125rem;
  line-height: 1.5;
  text-align: center;
  overflow-wrap: anywhere;
}
.camera-card__state--passed {
  background: #e4efe6;
  color: #326143;
}
.camera-card__state--failed {
  background: #fae9df;
  color: #925b3a;
}
.camera-card__footer {
  align-items: center;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e9ece3;
}
.camera-card__footer .button {
  gap: 8px;
  min-height: 44px;
  font-size: 0.8125rem;
}
.selected-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #426749;
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.5;
}
@media (max-width: 640px) {
  .devices-screen {
    padding: 28px 0 46px;
  }
  .devices-screen__header h1 {
    font-size: 1.625rem;
  }
}
@media (max-width: 360px) {
  .camera-card__heading {
    flex-direction: column;
  }
  .camera-card__state {
    max-width: 100%;
  }
}
</style>
