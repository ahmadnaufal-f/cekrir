<script setup lang="ts">
import { computed, nextTick, onUnmounted, shallowRef, watch } from 'vue'
import { RouterLink } from 'vue-router'
import EspFirmwareGenerator from '../components/EspFirmwareGenerator.vue'
import AppIcon from '../components/AppIcon.vue'
import TabSelector from '../components/TabSelector.vue'
import DeviceCard from '../components/DeviceCard.vue'
import DeviceRegistrationDialog from '../components/DeviceRegistrationDialog.vue'
import DeviceManagementDialog from '../components/DeviceManagementDialog.vue'
import PageHeader from '../components/PageHeader.vue'
import { adminCopy } from '../lib/admin-copy'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import { isDeviceSetupComplete } from '../lib/device-setup-state'
import { configuredReference, esp32SetupContent } from '../lib/setup-reference'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { CameraSummary, DeviceInventory } from '../types/app'
import type {
  DeviceCategory,
  DeviceUser,
  SetupStatus,
  TabOption,
} from '../types/device-ui'

const props = defineProps<{
  services?: Pick<AppServices, 'mode' | 'devices'>
  user: DeviceUser
  category: DeviceCategory
  registrationRequest?: DeviceCategory | null
}>()
const emit = defineEmits<{
  sessionExpired: []
  'update:category': [category: DeviceCategory]
  registrationHandled: []
}>()

type Esp32Action = 'rename-esp32' | 'remove-esp32'
type DeviceDialog =
  | { action: 'register'; category: DeviceCategory }
  | { action: Esp32Action; device: NonNullable<DeviceInventory['esp32']> }
  | { action: 'edit-camera' | 'remove-camera'; device: CameraSummary }

const categories: readonly DeviceCategory[] = ['esp32', 'bardi']
const copy = adminCopy.devices
const esp32SourceHref = configuredReference(esp32SetupContent, 'source')
const inventory = shallowRef<DeviceInventory | null>(null)
const inventoryState = shallowRef<'loading' | 'ready' | 'error'>('loading')
const selecting = shallowRef(false)
const errorMessage = shallowRef('')
const noticeMessage = shallowRef('')
const dialog = shallowRef<DeviceDialog | null>(null)
const deviceKey = shallowRef<string | null>(null)
const provisioning = shallowRef(false)
const isAdmin = computed(() => props.user.role === 'admin')
const selectedCameraId = computed(
  () => inventory.value?.selectedDeliveryCameraId ?? null,
)
const esp32Description = computed(() =>
  inventory.value?.esp32 ? copy.esp32ManageDescription : copy.esp32Description,
)
function status(category: DeviceCategory): SetupStatus | undefined {
  if (!props.services) return undefined
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
    dialog.value = null
    emit('sessionExpired')
    return true
  }
  return false
}
async function loadInventory() {
  const services = props.services
  if (!services) return
  const request = ++generation
  inventoryState.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await services.devices.inventory()
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
async function provisionEsp() {
  if (!props.services || !inventory.value?.esp32 || provisioning.value) return
  if (
    !window.confirm(
      'Creating a key will invalidate the existing ESP key. Continue?',
    )
  )
    return
  const request = generation
  provisioning.value = true
  deviceKey.value = null
  try {
    const result = await props.services.devices.registerEsp32(
      inventory.value.esp32.name,
    )
    if (!isCurrent(request)) return
    inventory.value = result.inventory
    deviceKey.value = result.credential || null
  } catch (cause) {
    if (isCurrent(request) && !reportUnauthorized(cause, request))
      errorMessage.value = copy.esp32Failed
  } finally {
    if (isCurrent(request)) provisioning.value = false
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
    dialog.value ||
    inventoryState.value !== 'ready'
  )
    return
  if (category === 'esp32' && inventory.value.esp32) {
    noticeMessage.value = copy.esp32Limit
    return
  }
  dialog.value = { action: 'register', category }
}
function openEsp32Management(action: Esp32Action) {
  const device = inventory.value?.esp32
  if (!isAdmin.value || !device || selecting.value || dialog.value) return
  dialog.value = { action, device }
}
function openCameraManagement(
  action: 'edit-camera' | 'remove-camera',
  device: CameraSummary,
) {
  if (!isAdmin.value || selecting.value || dialog.value) return
  dialog.value = { action, device }
}
function applyInventory(result: DeviceInventory) {
  inventory.value = result
  inventoryState.value = 'ready'
  errorMessage.value = ''
  noticeMessage.value = ''
}
function saved(result: DeviceInventory) {
  applyInventory(result)
  if (dialog.value?.action === 'edit-camera')
    noticeMessage.value = copy.cameraUpdated
}
function managed(result: DeviceInventory) {
  const operation = dialog.value
  if (
    !operation ||
    operation.action === 'register' ||
    operation.action === 'edit-camera'
  )
    return
  const removedDeliveryCamera =
    operation.action === 'remove-camera' &&
    operation.device.id === selectedCameraId.value
  applyInventory(result)
  switch (operation.action) {
    case 'rename-esp32':
      noticeMessage.value = copy.esp32Renamed
      break
    case 'remove-esp32':
      noticeMessage.value = copy.esp32Removed
      break
    case 'remove-camera':
      noticeMessage.value =
        removedDeliveryCamera && result.cameras.length
          ? copy.deliveryCameraRemoved
          : copy.cameraRemoved
      break
  }
  void closeDeviceDialog()
}
async function closeDeviceDialog() {
  dialog.value = null
  await nextTick()
  // A removed control cannot receive focus after the dialog closes.
  if (document.activeElement === document.body)
    document
      .getElementById(`device-tabs-${props.category}`)
      ?.focus({ preventScroll: true })
}
async function selectCamera(cameraId: string) {
  const services = props.services
  if (
    !services ||
    !isAdmin.value ||
    selecting.value ||
    dialog.value ||
    !inventory.value?.cameras.some((camera) => camera.id === cameraId)
  )
    return
  const request = generation
  selecting.value = true
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const result = await services.devices.selectCamera(cameraId)
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
    deviceKey.value = null
    inventory.value = null
    selecting.value = false
    dialog.value = null
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
  deviceKey.value = null
})
</script>

<template>
  <section class="devices-screen" aria-labelledby="devices-title">
    <PageHeader :title="copy.title" title-id="devices-title">
      <p>{{ copy.intro }}</p>
    </PageHeader>
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
      <p v-if="services" class="devices-screen__status-note content-inset">
        {{
          services.mode === 'mock'
            ? 'Mode demo. Perangkat dan pengaturannya disimulasikan.'
            : ''
        }}
        {{ copy.setupStatusNote }}
      </p>
      <p v-else class="banner">
        {{ deviceGuideCopy.common.registrationUnavailable }}
      </p>
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
        :aria-busy="!!services && inventoryState === 'loading'"
        tabindex="0"
      >
        <header class="device-panel__heading content-inset">
          <h2>
            {{
              panelCategory === 'esp32' ? copy.esp32Title : copy.camerasTitle
            }}
          </h2>
          <AppIcon :name="panelCategory === 'esp32' ? 'device' : 'camera'" />
        </header>
        <p v-if="services" class="device-panel__description content-inset">
          {{
            panelCategory === 'esp32'
              ? esp32Description
              : copy.camerasDescription
          }}
        </p>
        <p
          v-if="services && inventoryState === 'loading'"
          class="device-panel__state"
          role="status"
        >
          {{ adminCopy.common.loading }}
        </p>
        <div
          v-else-if="services && inventoryState === 'error'"
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
            <ul v-if="inventory.esp32" class="device-list">
              <li>
                <DeviceCard
                  :id="inventory.esp32.id"
                  :name="inventory.esp32.name"
                  :description="copy.esp32Registered"
                  :edit-label="copy.editEsp32"
                  :busy="selecting"
                  @edit="openEsp32Management('rename-esp32')"
                  @remove="openEsp32Management('remove-esp32')"
                />
              </li>
            </ul>
            <p v-else class="device-panel__empty content-inset">
              {{ copy.noEsp32 }}
            </p>
          </template>
          <template v-else>
            <p
              v-if="!inventory.cameras.length"
              class="device-panel__empty content-inset"
            >
              {{ copy.camerasEmpty }}
            </p>
            <ul v-else class="device-list">
              <li v-for="camera in inventory.cameras" :key="camera.id">
                <DeviceCard
                  :id="camera.id"
                  :name="camera.name"
                  :description="
                    camera.configurationState === 'configured'
                      ? copy.cameraConfigured
                      : copy.cameraIncomplete
                  "
                  :edit-label="copy.editCamera"
                  :busy="selecting"
                  @edit="openCameraManagement('edit-camera', camera)"
                  @remove="openCameraManagement('remove-camera', camera)"
                >
                  <template #badge>
                    <span
                      class="camera-verification"
                      :class="`camera-verification--${camera.verificationState}`"
                      >{{ cameraVerificationLabel(camera) }}</span
                    >
                  </template>
                  <template #actions>
                    <span
                      v-if="selectedCameraId === camera.id"
                      class="selected-label"
                      aria-current="true"
                      ><AppIcon name="check" />{{ copy.selectedCamera }}</span
                    >
                    <button
                      v-else
                      class="button button--quiet camera-select"
                      type="button"
                      :disabled="selecting"
                      @click="selectCamera(camera.id)"
                    >
                      <AppIcon name="camera" />{{
                        selecting ? copy.selectingCamera : copy.selectCamera
                      }}
                    </button>
                  </template>
                </DeviceCard>
              </li>
            </ul>
          </template>
        </template>
        <div
          v-if="panelCategory === 'esp32' || !services || inventory"
          class="device-panel__actions content-inset"
          :class="{
            'device-panel__actions--registered':
              panelCategory === 'esp32' && inventory?.esp32,
          }"
        >
          <button
            v-if="
              services?.mode === 'live' &&
              panelCategory === 'esp32' &&
              inventory?.esp32
            "
            class="button button--quiet"
            type="button"
            :disabled="provisioning"
            @click="provisionEsp"
          >
            Create or rotate ESP key
          </button>
          <RouterLink
            v-if="
              panelCategory === 'esp32' ||
              !services ||
              (inventory && !isDeviceSetupComplete(inventory, panelCategory))
            "
            class="button button--quiet device-panel__guide"
            :to="{
              name: panelCategory === 'esp32' ? 'esp32-setup' : 'bardi-setup',
            }"
          >
            <AppIcon name="book" />{{
              panelCategory === 'esp32' ? copy.guideEsp32 : copy.guideCamera
            }}
          </RouterLink>
          <a
            v-if="
              panelCategory === 'esp32' && inventory?.esp32 && esp32SourceHref
            "
            class="button button--quiet device-panel__source"
            :href="esp32SourceHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            <AppIcon name="external" />{{ deviceGuideCopy.esp32.sourceLink }}
          </a>
          <button
            v-if="inventory && (panelCategory === 'bardi' || !inventory.esp32)"
            class="button button--primary"
            type="button"
            :disabled="selecting"
            @click="openRegistration(panelCategory)"
          >
            <AppIcon name="plus" />{{ copy.registerDevice }}
          </button>
        </div>
        <EspFirmwareGenerator
          v-if="panelCategory === 'esp32' && inventory?.esp32 && deviceKey"
          :device-id="inventory.esp32.id"
          :device-key="deviceKey"
        />
      </section>
      <DeviceRegistrationDialog
        v-if="
          services &&
          inventory &&
          (dialog?.action === 'register' || dialog?.action === 'edit-camera')
        "
        :services="services"
        :user="user"
        :kind="dialog.action === 'register' ? dialog.category : 'bardi'"
        :inventory="inventory"
        :camera-to-edit="
          dialog.action === 'edit-camera' ? dialog.device : undefined
        "
        @saved="saved"
        @close="closeDeviceDialog"
        @session-expired="emit('sessionExpired')"
      />
      <DeviceManagementDialog
        v-else-if="
          services &&
          dialog &&
          dialog.action !== 'register' &&
          dialog.action !== 'edit-camera'
        "
        :devices="services.devices"
        :device="dialog.device"
        :action="dialog.action"
        :clears-delivery-camera="
          dialog.action === 'remove-camera' &&
          selectedCameraId === dialog.device.id
        "
        @updated="managed"
        @close="closeDeviceDialog"
        @session-expired="emit('sessionExpired')"
      />
    </template>
  </section>
</template>

<style scoped>
.devices-screen {
  padding-bottom: 64px;
  color: #233d37;
}
.devices-screen > .banner {
  padding-inline: var(--card-inset);
}
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
  flex: none;
}
.device-panel__heading h2 {
  margin: 0;
  font-size: 1.125rem;
  line-height: 1.4;
}
.device-panel__state {
  margin: 24px 0;
  padding: 20px var(--card-inset);
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
.device-panel__actions--registered {
  display: flex;
  flex-wrap: wrap;
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
.device-panel__actions--registered .button {
  gap: 6px;
  padding: 0;
  background: transparent;
  color: #234e41;
  font-size: 0.8125rem;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.device-panel__actions--registered .app-icon {
  width: 1em;
  height: 1em;
}
.device-list {
  display: grid;
  gap: 12px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}
.camera-verification {
  max-width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f0efe6;
  color: #6f6342;
  font-size: 0.8125rem;
  line-height: 1.5;
  text-align: center;
  overflow-wrap: anywhere;
}
.camera-verification--passed {
  background: #e4efe6;
  color: #326143;
}
.camera-verification--failed {
  background: #fae9df;
  color: #925b3a;
}
.camera-select {
  gap: 8px;
  text-align: start;
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
    padding-bottom: 46px;
  }
}
</style>
