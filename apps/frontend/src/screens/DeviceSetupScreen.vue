<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import BackButton from '../components/BackButton.vue'
import DeviceSetupGuide from '../components/DeviceSetupGuide.vue'
import PageHeader from '../components/PageHeader.vue'
import SetupStepCarousel from '../components/SetupStepCarousel.vue'
import { adminCopy } from '../lib/admin-copy'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import {
  ServiceError,
  type AppServices,
  type DeviceService,
} from '../services/contracts'
import type { DeviceCategory, DeviceUser } from '../types/device-ui'

const props = defineProps<{
  services: Pick<AppServices, 'setup'>
  user: DeviceUser
  kind: DeviceCategory
  devices?: Pick<DeviceService, 'inventory'>
}>()

const emit = defineEmits<{
  back: []
  register: []
  sessionExpired: []
}>()

const copy = computed(() => deviceGuideCopy[props.kind])
const activeStep = shallowRef(0)
const registrationState = shallowRef<
  'loading' | 'empty' | 'registered' | 'error'
>('loading')
const retryInventory = shallowRef(0)
const canRegister = computed(
  () =>
    !!props.devices &&
    (props.kind === 'bardi' || registrationState.value === 'empty'),
)
const subtitle = computed(() => {
  if (!props.devices) return deviceGuideCopy.common.registrationUnavailable
  if (props.kind === 'esp32' && registrationState.value === 'registered')
    return deviceGuideCopy.esp32.registeredSubtitle
  return copy.value.subtitle
})

watch(
  () =>
    [
      props.kind,
      props.devices,
      props.user.id,
      props.user.householdId,
      retryInventory.value,
    ] as const,
  async ([kind, devices], _, onCleanup) => {
    if (kind !== 'esp32' || !devices) return
    let current = true
    onCleanup(() => (current = false))
    registrationState.value = 'loading'
    try {
      const inventory = await devices.inventory()
      if (current)
        registrationState.value = inventory.esp32 ? 'registered' : 'empty'
    } catch (cause) {
      if (!current) return
      registrationState.value = 'error'
      if (
        cause instanceof ServiceError &&
        (cause.status === 401 || cause.code === 'UNAUTHENTICATED')
      )
        emit('sessionExpired')
    }
  },
  { immediate: true },
)
</script>

<template>
  <section
    class="device-setup-screen focused-page"
    :aria-labelledby="`${kind}-setup-title`"
  >
    <div class="sticky-header focused-page__back">
      <BackButton label="Kembali ke perangkat" @click="emit('back')" />
    </div>
    <div class="focused-page__content">
      <PageHeader
        class="focused-page__heading"
        :title="copy.title"
        :title-id="`${kind}-setup-title`"
      >
        <p>{{ subtitle }}</p>
        <p class="device-setup-screen__disclaimer">
          {{ deviceGuideCopy.common.illustrationDisclaimer }}
        </p>
      </PageHeader>

      <SetupStepCarousel
        v-model:active-index="activeStep"
        :label="copy.title"
        :steps="copy.steps"
      />

      <div
        v-if="devices && kind === 'esp32' && registrationState === 'error'"
        class="content-inset device-setup-screen__inventory-error"
        role="alert"
      >
        <p>{{ adminCopy.devices.loadFailed }}</p>
        <button class="text-button" type="button" @click="retryInventory++">
          {{ adminCopy.common.retry }}
        </button>
      </div>

      <div
        v-if="canRegister && activeStep === copy.steps.length - 1"
        class="device-setup-screen__actions content-inset"
      >
        <button
          class="device-setup-screen__register"
          type="button"
          @click="emit('register')"
        >
          <AppIcon name="plus" />
          {{ copy.registerAction }}
        </button>
      </div>

      <DeviceSetupGuide
        :services="services"
        :user="user"
        :kind="kind"
        @session-expired="emit('sessionExpired')"
      />
    </div>
  </section>
</template>

<style scoped>
.device-setup-screen {
  padding-bottom: 52px;
  color: #233d37;
}

.device-setup-screen__disclaimer {
  font-size: 0.8125rem;
}

.device-setup-screen__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.device-setup-screen__inventory-error {
  display: grid;
  justify-items: start;
  margin-top: 16px;
  color: #8c4226;
}

.device-setup-screen__inventory-error .text-button {
  padding-inline: 0;
}

.device-setup-screen__register {
  display: inline-flex;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 11px 16px;
  border: 0;
  border-radius: 8px;
  background: #234e41;
  color: #f6f7f2;
  font-size: 0.875rem;
  font-weight: 680;
}

.device-setup-screen__register:hover {
  background: #173e32;
}

@media (max-width: 620px) {
  .device-setup-screen {
    padding-bottom: 40px;
  }

  .device-setup-screen__actions {
    margin-top: 12px;
  }

  .device-setup-screen__register {
    width: 100%;
  }
}
</style>
