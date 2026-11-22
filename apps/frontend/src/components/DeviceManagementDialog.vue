<script setup lang="ts">
import {
  computed,
  onMounted,
  onUnmounted,
  shallowRef,
  useTemplateRef,
} from 'vue'
import AppDialog from './AppDialog.vue'
import { adminCopy } from '../lib/admin-copy'
import { ui } from '../lib/strings'
import { ServiceError, type DeviceService } from '../services/contracts'
import type { CameraSummary, DeviceInventory } from '../types/app'

export type DeviceManagementAction =
  | 'rename-esp32'
  | 'remove-esp32'
  | 'remove-camera'

const props = defineProps<{
  devices: Pick<DeviceService, 'renameEsp32' | 'removeEsp32' | 'removeCamera'>
  device: Pick<CameraSummary, 'id' | 'name'>
  action: DeviceManagementAction
  clearsDeliveryCamera?: boolean
}>()
const emit = defineEmits<{
  updated: [inventory: DeviceInventory]
  close: []
  sessionExpired: []
}>()

const copy = adminCopy.devices
const renaming = computed(() => props.action === 'rename-esp32')
const operations = {
  'rename-esp32': {
    title: copy.renameEsp32Title,
    description: undefined,
    failure: copy.esp32RenameFailed,
    save: (id: string, label: string) => props.devices.renameEsp32(id, label),
  },
  'remove-esp32': {
    title: copy.removeEsp32Title,
    description: copy.removeEsp32Description,
    failure: copy.esp32RemoveFailed,
    save: (id: string) => props.devices.removeEsp32(id),
  },
  'remove-camera': {
    title: copy.removeCameraTitle,
    description: copy.removeCameraDescription,
    failure: copy.cameraRemoveFailed,
    save: (id: string) => props.devices.removeCamera(id),
  },
}
const operation = computed(() => operations[props.action])
const description = computed(() =>
  props.clearsDeliveryCamera
    ? copy.removeDeliveryCameraDescription
    : operation.value.description,
)
const submitLabel = computed(() => {
  if (renaming.value) return pending.value ? ui.saving : copy.saveChanges
  return pending.value ? copy.removingDevice : copy.removeDevice
})
const name = shallowRef(props.device.name)
const nameField = useTemplateRef<HTMLInputElement>('nameField')
const pending = shallowRef(false)
const errorMessage = shallowRef('')
const nameError = shallowRef('')
let disposed = false

async function submit() {
  if (pending.value) return
  const label = name.value.trim()
  errorMessage.value = ''
  nameError.value = ''
  if (renaming.value && !label) {
    nameError.value = copy.esp32NameRequired
    nameField.value?.focus()
    return
  }

  pending.value = true
  try {
    const inventory = await operation.value.save(props.device.id, label)
    if (!disposed) emit('updated', inventory)
  } catch (cause) {
    if (disposed) return
    if (
      cause instanceof ServiceError &&
      (cause.status === 401 || cause.code === 'UNAUTHENTICATED')
    ) {
      emit('sessionExpired')
    } else if (
      renaming.value &&
      cause instanceof ServiceError &&
      cause.fieldErrors.name
    ) {
      nameError.value = cause.fieldErrors.name
    } else {
      errorMessage.value = operation.value.failure
    }
  } finally {
    pending.value = false
  }
}

onMounted(() => nameField.value?.focus())
onUnmounted(() => {
  disposed = true
})
</script>

<template>
  <AppDialog
    :title="operation.title"
    :description="description"
    :busy="pending"
    @close="emit('close')"
  >
    <form class="api-form" @submit.prevent="submit">
      <label v-if="renaming">
        {{ copy.esp32Name }}
        <input
          ref="nameField"
          v-model="name"
          required
          maxlength="80"
          autocomplete="off"
          :readonly="pending"
          :aria-invalid="!!nameError || undefined"
          :aria-describedby="
            nameError ? 'device-management-name-error' : undefined
          "
          @input="nameError = ''"
        />
        <span
          v-if="nameError"
          id="device-management-name-error"
          class="field-error"
        >
          {{ nameError }}
        </span>
      </label>
      <p v-else class="device-management__name">
        <strong>{{ device.name }}</strong>
      </p>

      <p v-if="errorMessage" class="field-error" role="alert">
        {{ errorMessage }}
      </p>
      <div class="device-management__actions">
        <button
          class="button button--quiet"
          type="button"
          :disabled="pending"
          @click="emit('close')"
        >
          Batal
        </button>
        <button
          class="button button--primary"
          :class="{ 'device-management__remove': !renaming }"
          type="submit"
          :disabled="pending || (renaming && name.trim() === device.name)"
        >
          {{ submitLabel }}
        </button>
      </div>
    </form>
  </AppDialog>
</template>

<style scoped>
.device-management__name {
  overflow-wrap: anywhere;
}
.device-management__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
.device-management__remove {
  background: #8d3729;
}
.device-management__remove:hover:not(:disabled) {
  background: #69281e;
}
</style>
